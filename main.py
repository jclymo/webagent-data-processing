import os
from db import MongoDB
from dotenv import load_dotenv
from actions import event_to_action, Action
from observation import DOMObservation

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

def argmax_less_than(search_list, value):
    if len(search_list) == 0 or search_list[0] >= value:
        return False
    
    i = 0
    while i+1 < len(search_list):
        if search_list[i+1] >= value:
            return i
        i += 1
    
    # final element is best match
    return len(search_list) - 1

def postprocess_document(document):
    # separate html and events
    html_log, event_log = split_observation_and_event_logs(document['data'])
    html_log.sort(key = lambda x: x["timestamp"])
    event_log.sort(key = lambda x: x["timestamp"])
    html_times = [capture["timestamp"] for capture in html_log]

    # reduce event log to key events only
    event_log = combine_input_events(event_log)
    
    # map events to actions
    # recombine, interleaving observations and actions
    combined_log = []
    for event in event_log:
        action = event_to_action(event)
        if not action:
            continue
        
        if not isinstance(action, list):
            action = [action]
        start_time = action[0].timestamp
        if i := argmax_less_than(html_times, start_time):
            combined_log.append(DOMObservation(html_log[i]))

        combined_log.extend(action)

    return combined_log

def main():
    # Initialize database connection
    mongo = MongoDB()
    documents = []
    
    try:
        # Example: Get one event record by url 
        # TODO get all unprocessed records
        event_id = "some_event_id"
        # documents = mongo.get_by_url("https://huggingface.co/learn/llm-course/en/chapter5/4")
        documents = mongo.get_by_timestamp(1762444020)
        # process all events
        for document in documents: 
            trajectory = postprocess_document(document)
            for item in trajectory:
                if isinstance(item, Action):
                    print(item.bg_action, item.timestamp)
                else:
                    print(item.ax_tree, item.timestamp)
                print("-----"*30)

    finally:
        # Always close connection when done
        mongo.close()

if __name__ == "__main__":
    main()