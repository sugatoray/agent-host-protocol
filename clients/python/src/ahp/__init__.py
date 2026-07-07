"""Python client for the Agent Host Protocol (AHP).

Quick start::

    from ahp import AhpClient
    from ahp.transport import WebSocketTransport

    async with AhpClient(await WebSocketTransport.connect("ws://localhost:1234")) as client:
        root_state = await client.initialize()
        session_state = await client.subscribe(some_session_uri)

See SPEC.md for the full design and phased build history, and CHANGELOG.md
for what's landed so far.
"""

from .client import AhpClient, AhpClientError, ResourceProvider
from .hosts import MultiHostClient, MultiHostClientError

# __version__ = "0.1.0.dev0"

try:
    from importlib import metadata
except ImportError:  # for Python<3.8
    import importlib_metadata as metadata

__libname__ = "ahp"
__title__ = __name__ if __name__ == __libname__ else __libname__.replace("-", "_")  # type: ignore
__version__ = metadata.version(__title__)  # type: ignore

__all__ = [
    "AhpClient",
    "AhpClientError",
    "ResourceProvider",
    "MultiHostClient",
    "MultiHostClientError",
    "__version__",
]

