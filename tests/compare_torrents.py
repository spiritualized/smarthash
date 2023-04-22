from BitTornado.Meta.bencode import bdecode


def compare_torrents(torrent_1_in, torrent_2_in) -> bool:
    torrent_1 = bdecode(torrent_1_in)
    torrent_2 = bdecode(torrent_2_in)

    for ignorable_field in ['creation date', 'comment', 'smarthash_version']:
        del torrent_1[ignorable_field]
        del torrent_2[ignorable_field]

    return torrent_1 == torrent_2
