import os
import streamlit.components.v1 as components

# Get the path to the component directory
_RELEASE = True

if not _RELEASE:
    _av_interview = components.declare_component(
        "av_interview",
        url="http://localhost:3001",
    )
else:
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    _av_interview = components.declare_component("av_interview", path=parent_dir)

def av_interview(ai_speaking: bool = False, key=None):
    """
    Creates a new instance of the custom AV Interview component.
    """
    component_value = _av_interview(ai_speaking=ai_speaking, key=key, default=None)
    return component_value
