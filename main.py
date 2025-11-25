import os
from db import MongoDB
from dotenv import load_dotenv
from actions import event_to_action, Action
from observation import DOMObservation
import json
from bs4 import BeautifulSoup
from s3 import S3Handler
from urllib.parse import urlparse

# Load environment variables (optional if already loaded in db.py)
load_dotenv()

def split_observation_and_event_logs(full_log):
    html_log, event_log = [], []
    for entry in full_log:
        if entry['type'] == 'htmlCapture':
            html_log.append(entry)
        else:
            event_log.append(entry)
    return html_log, event_log

def combine_input_events(event_log):
    new_event_log = []
    start_of_sequence = 0
    for i, event in enumerate(event_log):
        if event['type'] == 'input':
            if start_of_sequence == 0:
                start_of_sequence = event['timestamp']
            if i < len(event_log)-1 and event['target']['bid'] == event_log[i+1]['target']['bid']:
                continue # skip this event
        # end of input sequence. Save and prepare for next seq
        event['start_timestamp'] = start_of_sequence
        start_of_sequence = 0
        new_event_log.append(event)
    return new_event_log           

def pair_event_obs(events, observations):
    ans = []
    i = j = 0
    while i < len(events) and j < len(observations):
        if observations[j]["timestamp"] < events[i]["timestamp"]:
            # Check if they are consecutive with no timestamp in between
            # meaning: next timestamp among (obs[j+1], events[i-1]) must not lie between
            prev_event = events[i-1] if i > 0 else None
            next_obs = observations[j+1] if j+1 < len(observations) else None
            
            # Condition: no timestamp between obs[j] and events[i]
            valid = True
            
            if next_obs is not None and observations[j]["timestamp"] < next_obs["timestamp"] < events[i]["timestamp"]:
                valid = False
            if prev_event is not None and observations[j]["timestamp"] < prev_event["timestamp"] < events[i]["timestamp"]:
                valid = False
            
            if valid:
                ans.append([observations[j], events[i]])
                j += 1
                i += 1
            else:
                j += 1
        else:
            i += 1
    return ans

def postprocess_document(document):
    # separate html and events
    html_log, event_log = split_observation_and_event_logs(document['data'])
    html_log.sort(key = lambda x: x["timestamp"])
    event_log.sort(key = lambda x: x["timestamp"])

    # reduce event log to key events only
    event_log = combine_input_events(event_log)
    
    # map events to actions
    pairs = []
    result = pair_event_obs(event_log, html_log)
    s3 = S3Handler()
    for obs, event in result:
        action = event_to_action(event)
        if not action:
            # print("No action for event:", obs["timestamp"], event["timestamp"])
            # print(event["type"])
            continue
        if not isinstance(action, list):
            action = [action]
        
        html_url = obs.get("html_file_url", "")
        if html_url != "":
            parsed = urlparse(html_url)
            s3_object_key = parsed.path.lstrip("/")
            file_path = s3.download_file(s3_object_key)
            with open(file_path, "r") as f:
                html_content = f.read()
                obs["html"] = html_content
        pairs.append([DOMObservation(obs), action])
    return pairs

def main():
    # Initialize database connection
    mongo = MongoDB()
    documents = []
    
    try:
        documents = mongo.get_latest()
        # processed = mongo.get_post_process_by_taskid(documents["_id"])
        # if (processed):
        #     print("Already processed")
        #     return
        # process all events
        for document in documents: 
            trajectory = postprocess_document(document)
            
            #  construct training data
            payload = []
            for idx, (obs, actions) in enumerate(trajectory):
                # print('obs: ',obs.timestamp, 'event: ',actions[0].timestamp)
                data_bids = [action.bg_action.get("data_bid", "") for action in actions]
                print('data_bids: ', data_bids)
                soup = BeautifulSoup(obs.bg_html, "html.parser")
                elems = [soup.find(attrs={"data-bid": data_bid}) for data_bid in data_bids]
                if not elems or any(elem is None for elem in elems):
                    print(f"Skipping step {idx} due to missing elements for data_bids: {data_bids}")
                    continue
                data = {
                    "step": idx + 1,
                    "task_description": document.get("task_description", ""),
                    "bid": [elem.attrs["bid"] for elem in elems],
                    "action": [{k: v for k, v in action.bg_action.items() if k != "data_bid"} for action in actions],
                    "video_timestamp": [action.video_timestamp for action in actions],
                    "axtree": obs.bg_axtree,
                    "raw_data_id": str(document["_id"])
                }
                payload.append(data)
            if len(payload) > 0:
                print(f"Inserting {len(payload)} processed steps for document ID {document['_id']}")
                mongo.insert_post_process(payload)

    finally:
        # Always close connection when done
        mongo.close()

if __name__ == "__main__":
    main()