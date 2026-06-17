import os
import streamlit.components.v1 as components

_COMPONENT_DIR = os.path.dirname(os.path.abspath(__file__))

_component_func = components.declare_component(
    "webcam_proctor",
    path=_COMPONENT_DIR,
)

def webcam_proctor(capture_interval_seconds=30, key=None, height=430):
    """
    Renders a webcam proctor component.

    Returns:
        str | None:
            Latest captured webcam frame as a data URL:
            data:image/jpeg;base64,...
    """
    return _component_func(
        capture_interval_seconds=capture_interval_seconds,
        key=key,
        default=None,
        height=height,
    )
