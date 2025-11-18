import gymnasium as gym
import browsergym.core
from browsergym.utils.obs import flatten_dom_to_str, flatten_axtree_to_str
import json
import pathlib
import tempfile, os


def has_focusable_property(node):
    """Return True if node has a 'focusable' property."""
    for prop in node.get("properties", []):
        if prop.get("name") == "focusable":
            return True
    return False


def filter_focusable_nodes(data):
    """Keep only nodes that have the 'focusable' property, preserving full structure."""
    focusable_nodes = [
        node for node in data.get("nodes", []) if has_focusable_property(node)
    ]
    # print('focusable_nodes length:', len(focusable_nodes))
    return {"nodes": focusable_nodes}


def add_bounding_boxes(env, axtree):
    """Attach bounding boxes (x, y, width, height) to each node with backendDOMNodeId."""
    # Open a DevTools session for CDP commands
    page = env.unwrapped.browser.contexts[0].pages[0]
    client = page.context.new_cdp_session(page)

    for node in axtree["nodes"]:
        bid = node.get("backendDOMNodeId")
        if not bid:
            continue
        try:
            box = client.send("DOM.getBoxModel", {"backendNodeId": bid})
            content = box["model"]["content"]
            x_coords = content[::2]
            y_coords = content[1::2]
            bbox = {
                "x": (min(x_coords) + max(x_coords))/2,
                "y": (min(y_coords) + max(y_coords))/2,
                # "width": max(x_coords) - min(x_coords),
                # "height": max(y_coords) - min(y_coords),
            }
            node["boundingBox"] = bbox
        except Exception as e:
            node["boundingBox"] = None  # e.g., off-screen or hidden
    return axtree


def generate_axtree(html_string):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as f:
        f.write(html_string.encode("utf-8"))
        file_url = "file://" + f.name
    
    # abs_path = pathlib.Path(file_url).resolve().as_uri()
    try:
        env = gym.make(
            "browsergym/openended",
            task_kwargs={"start_url": file_url},  # starting URL
            wait_for_user_message=False,
            # viewport={"width": 1728, "height": 992},
            resizeable_window=True
        )
        
        obs, info = env.reset()
        axtree = obs["axtree_object"]
        if not axtree:
            raise RuntimeError("Accessibility tree not found in observation")
        axtree = filter_focusable_nodes(axtree)
        html = flatten_dom_to_str(obs["dom_object"])
        return axtree, html
    
    finally:
        env.close()
        if os.path.exists(f.name):
            os.remove(f.name)
    # dst_filename = "axtree/" + filename.replace(".html", ".json")
    # print('numbers of nodes in axtree:', len(axtree["nodes"]))
    # with open(dst_filename, "w") as f:
    #     f.write(json.dumps(axtree, indent=2))
    env.close()
    

class DOMObservation:
    def __init__(self, htmlCapture):
        self.raw_obs = htmlCapture
        [bg_axtree, bg_html] = generate_axtree(htmlCapture.get("html", ""))
        self.bg_axtree = bg_axtree
        self.bg_html = bg_html
        self._set_times()

    def _set_times(self):
        # print(type(self.raw_obs))
        # print(self.raw_obs["timestamp"])
        self.timestamp = self.raw_obs["timestamp"]
        self.video_timestamp = self.raw_obs["video_timestamp"]

    @property
    def html(self):
        return self.raw_obs["html"]#[:500] # for demo / testing

        # return self.raw_obs["html"] 