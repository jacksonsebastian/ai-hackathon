import os
import streamlit.components.v1 as components

_component_func = components.declare_component(
    "webcam_auto",
    path=os.path.dirname(os.path.abspath(__file__))
)

def webcam_auto(capture_interval_seconds=30, key=None):
    """
    Renders an invisible background webcam component that captures frames at a set interval.
    Returns the latest base64 encoded image string if a capture occurred.
    """
    component_value = _component_func(capture_interval_seconds=capture_interval_seconds, key=key)
    return component_value
