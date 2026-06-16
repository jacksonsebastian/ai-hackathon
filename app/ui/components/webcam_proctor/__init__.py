import os
import streamlit.components.v1 as components

_component_func = components.declare_component(
    "webcam_proctor",
    path=os.path.dirname(os.path.abspath(__file__))
)

def webcam_proctor(capture_interval_seconds=30, key=None):
    """
    Renders a background webcam component that captures frames at a set interval.
    Returns the latest base64 encoded image string if a capture occurred.
    """
    component_value = _component_func(capture_interval_seconds=capture_interval_seconds, key=key)
    return component_value
