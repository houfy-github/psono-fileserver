from rest_framework import status
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.core.files.storage import get_storage_class
from rest_framework import serializers, exceptions

from ..utils import get_ip, APIServer

import pyblake2


class UploadSerializer(serializers.Serializer):

    def validate(self, attrs: dict) -> dict:

        token = self.context['request'].data.get('token', None)
        chunk = self.context['request'].data.get('chunk', None)
        ticket = self.context['request'].data.get('ticket', None)
        ticket_nonce = self.context['request'].data.get('ticket_nonce', None)

        if token is None:
            msg = _("Token is required.")
            raise exceptions.ValidationError(msg)

        if chunk is None:
            msg = _("File is required.")
            raise exceptions.ValidationError(msg)

        if ticket is None:
            msg = _("Ticket is required.")
            raise exceptions.ValidationError(msg)

        if ticket_nonce is None:
            msg = _("Ticket nonce is required.")
            raise exceptions.ValidationError(msg)

        chunk_content = chunk.read()
        chunk.seek(0)

        chunk_size = len(chunk_content)
        hash_blake2b = pyblake2.blake2b(chunk_content).hexdigest()

        r = APIServer.query(
            method="PUT",
            endpoint="/authorize/upload/",
            data= {
                'token': token,
                'ticket': ticket,
                'ticket_nonce': ticket_nonce,
                'chunk_size': chunk_size,
                'hash_blake2b': hash_blake2b,
                'ip_address': get_ip(self.context['request']),
            },
        )

        if status.is_server_error(r.status_code):
            msg = _("Server is offline.")
            raise exceptions.ValidationError(msg)

        if not status.is_success(r.status_code):
            msg = _("Server is offline.")
            raise exceptions.ValidationError(msg)

        shard_id = r.json_decrypted.get('shard_id', None)

        if shard_id is None:
            msg = _("Shard ID is missing.")
            raise exceptions.ValidationError(msg)

        if shard_id not in settings.SHARDS_DICT:
            msg = _("Unknown Shard ID")
            raise exceptions.ValidationError(msg)

        shard_config = settings.SHARDS_DICT[shard_id]

        storage = get_storage_class(settings.AVAILABLE_FILESYSTEMS[shard_config['engine']['class']])(**shard_config['engine']['kwargs'])

        attrs['storage'] = storage
        attrs['chunk'] = chunk
        attrs['hash_blake2b'] = hash_blake2b

        return attrs
