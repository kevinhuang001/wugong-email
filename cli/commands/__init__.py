from .account import handle_account
from .list import handle_list
from .read import handle_read
from .delete import handle_delete
from .send import handle_send
from .sync import handle_sync
from .folder import handle_folder

__all__ = [
    "handle_account",
    "handle_list",
    "handle_read",
    "handle_delete",
    "handle_send",
    "handle_sync",
    "handle_folder",
]
