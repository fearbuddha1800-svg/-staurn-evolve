---
slug: signal_provenance
type: note
graph: gitnexus
---

"""Telegram receipt metadata only: never infers side, authorship, or reply destination."""
from datetime import datetime


def telegram_provenance(chat_id, msg):
    parent = getattr(msg, 'reply_to', None)
    reply_id = getattr(msg, 'reply_to_msg_id', None)
    if reply_id is None and parent is not None:
        reply_id = getattr(parent, 'reply_to_msg_id', None)
    peer = getattr(parent, 'reply_to_peer_id', None)
    # Cross-peer parents need explicit peer resolution, not an assumed local target.
    trace = f'{chat_id}:{reply_id}' if reply_id is not None and peer is None else None
    date = getattr(msg, 'date', None)
    edit = getattr(msg, 'edit_date', None)
    forward = getattr(msg, 'fwd_from', None)
    return {'platform': 'telegram', 'chat_id': str(chat_id),
            'message_id': getattr(msg, 'id', None), 'reply_message_id': reply_id,
            'reply_parent_trace': trace, 'cross_peer_reply': peer is not None,
            'posted_at': date.isoformat() if isinstance(date, datetime) else None,
            'edited_at': edit.isoformat() if isinstance(edit, datetime) else None,
            'is_forwarded': forward is not None,
            'forwarded_channel_post': getattr(forward, 'channel_post', None),
            'grouped_id': getattr(msg, 'grouped_id', None)}

## Links from
- [[daemon]]
- [[test_signal_provenance]]
