def format_line(k, v):
    return "{0}: {1}\n".format(k.ljust(41), v)


# noinspection DuplicatedCode
def mediainfo_to_string(mediainfo):

    out = ""

    for track in mediainfo:
        if 'text_format_list' in track:
            continue
        if track.get('format') == "RLE":
            continue

        # for k,v in track.items():
        # 	print(MIFormatLine(k,v), end="")

        if out != "":
            out += "\n"

        out += track['track_type']+"\n"

        if track['track_type'] == "General":
            if 'unique_id' in track:
                out += format_line("Unique ID", track['unique_id'])
            out += format_line("Complete name", track['complete_name'])
            out += format_line("Format", track['format'])
            if 'format_info' in track:
                out += format_line("Format/Info", track['format_info'])
            if 'format_version' in track:
                out += format_line("Format version", track['format_version'])
            out += format_line("File size", track['other_file_size'][0])
            out += format_line("Duration", track['other_duration'][0])
            if 'other_overall_bit_rate_mode' in track:
                out += format_line("Overall bit rate mode", track['other_overall_bit_rate_mode'][0])
            out += format_line("Overall bit rate", track['other_overall_bit_rate'][0])
            if 'encoded_date' in track:
                out += format_line("Encoded date", track['encoded_date'])
            if 'writing_application' in track:
                out += format_line("Writing application", track['writing_application'])
            if 'writing_library' in track:
                out += format_line("Writing library", track['writing_library'])

        elif track['track_type'] == "Video":

            out += format_line("ID", track['track_id'])
            out += format_line("Format", track['format'])
            if 'format_info' in track:
                out += format_line("Format/Info", track['format_info'])
            if 'format_profile' in track:
                out += format_line("Format profile", track['format_profile'])
            if 'format_settings' in track:
                out += format_line("Format settings", track['format_settings'])
            if 'format_settings__bvop' in track:
                out += format_line("Format settings, BVOP", track['format_settings__bvop'])
            if 'format_settings__qpel' in track:
                out += format_line("Format settings, QPel", track['format_settings__qpel'])
            if 'format_settings__gmc' in track:
                out += format_line("Format settings, GMC", track['format_settings__gmc'])
            if 'format_settings__matrix' in track:
                out += format_line("Format settings, Matrix", track['format_settings__matrix'])
            if 'codec_settings__cabac' in track:
                out += format_line("Format settings, CABAC", track['codec_settings__cabac'])
            if 'codec_settings_refframes' in track:
                out += format_line("Format settings, RefFrames", track['codec_settings_refframes'])
            if 'muxing_mode' in track:
                out += format_line("Muxing mode", track['muxing_mode'])
            if 'codec_id' in track:
                out += format_line("Codec ID", track['codec_id'])
            if 'codec_id_hint' in track:
                out += format_line("Codec ID/Hint", track['codec_id_hint'])
            if 'other_duration' in track:
                out += format_line("Duration", track['other_duration'][0])
            if 'other_bit_rate_mode' in track:
                out += format_line("Bit rate mode", track['other_bit_rate_mode'][0])
            if 'other_bit_rate' in track:
                out += format_line("Bit rate", track['other_bit_rate'][0])
            if 'other_maximum_bit_rate' in track:
                out += format_line("Maximum bit rate", track['other_maximum_bit_rate'][0])
            if 'overall_bit_rate_mode' in track:
                out += format_line("Overall bit rate mode", track['overall_bit_rate_mode'][0])
            if 'overall_bit_rate' in track:
                out += format_line("Overall bit rate", track['overall_bit_rate'][0])
            out += format_line("Width", track['other_width'][0])
            out += format_line("Height", track['other_height'][0])
            out += format_line("Display aspect ratio", track['other_display_aspect_ratio'][0])
            if 'other_frame_rate_mode' in track:
                out += format_line("Frame rate mode", track['other_frame_rate_mode'][0])
            if 'other_frame_rate' in track:
                out += format_line("Frame rate", track['other_frame_rate'][0])
            if 'other_original_frame_rate' in track:
                out += format_line("Frame rate mode", track['other_original_frame_rate'][0])
            if 'color_space' in track:
                out += format_line("Color space", track['color_space'])
            if 'chroma_subsampling' in track:
                out += format_line("Chroma subsampling", track['chroma_subsampling'])
            if 'other_bit_depth' in track:
                out += format_line("Bit depth", track['other_bit_depth'][0])
            if 'scan_type' in track:
                out += format_line("Scan type", track['scan_type'])
            if 'compression_mode' in track:
                out += format_line("Compression mode", track['compression_mode'])
            if 'bits__pixel_frame' in track:
                out += format_line("Bits/(Pixel*Frame)", track['bits__pixel_frame'])
            if 'other_stream_size' in track:
                out += format_line("Stream size", track['other_stream_size'][0])
            if 'other_writing_library' in track:
                out += format_line("Writing library", track['other_writing_library'][0])
            if 'encoding_settings' in track:
                out += format_line("Encoding settings", track['encoding_settings'])
            if 'other_language' in track:
                out += format_line("Language", track['other_language'][0])
            if 'default' in track:
                out += format_line("Default", track['default'])
            if 'forced' in track:
                out += format_line("Forced", track['forced'])
            if 'color_range' in track:
                out += format_line("Color range", track['color_range'])
            if 'color_primaries' in track:
                out += format_line("Color primaries", track['color_primaries'])
            if 'transfer_characteristics' in track:
                out += format_line("Transfer characteristics", track['transfer_characteristics'])
            if 'matrix_coefficients' in track:
                out += format_line("Matrix coefficients", track['matrix_coefficients'])

        elif track['track_type'] == "Audio":
            if 'track_id' in track:
                out += format_line("ID", track['track_id'])
            out += format_line("Format", track['format'])
            if 'format_version' in track:
                out += format_line("Format version", track['format_version'])
            if 'format_profile' in track:
                out += format_line("Format profile", track['format_profile'])
            if 'format_settings' in track:
                out += format_line("Format settings", track['format_settings'])
            if 'format_info' in track:
                out += format_line("Format/Info", track['format_info'])
            if 'codec_id' in track:
                out += format_line("Codec ID", track['codec_id'])
            if 'codec_id_hint' in track:
                out += format_line("Codec ID/Hint", track['codec_id_hint'])
            if 'other_duration' in track:
                out += format_line("Duration", track['other_duration'][0])
            if 'other_bit_rate_mode' in track:
                out += format_line("Bit rate mode", track['other_bit_rate_mode'][0])
            if 'other_bit_rate' in track:
                out += format_line("Bit rate", track['other_bit_rate'][0])
            if 'other_minimum_bit_rate' in track:
                out += format_line("Minimum bit rate", track['other_minimum_bit_rate'][0])
            out += format_line("Channel(s)", track['other_channel_s'][0])
            if 'channel_positions' in track:
                out += format_line("Channel positions", track['channel_positions'])
            out += format_line("Sampling rate", track['other_sampling_rate'][0])
            if 'other_frame_rate' in track:
                out += format_line("Frame rate", track['other_frame_rate'][0])
            if 'other_compression_mode' in track:
                out += format_line("Compression mode", track['other_compression_mode'][0])
            if 'other_stream_size' in track:
                out += format_line("Stream size", track['other_stream_size'][0])
            if 'other_alignment' in track:
                out += format_line("Alignment", track['other_alignment'][0])
            if 'other_interleave__duration' in track:
                out += format_line("Interleave, duration", track['other_interleave__duration'][1])
            if 'other_interleave__preload_duration' in track:
                out += format_line("Interleave, preload duration", track['other_interleave__preload_duration'][0])
            if 'writing_library' in track:
                out += format_line("Writing library", track['writing_library'])
            if 'encoding_settings' in track:
                out += format_line("Encoding settings", track['encoding_settings'])
            if 'other_language' in track:
                out += format_line("Language", track['other_language'][0])
            if 'other_service_kind' in track:
                out += format_line("Service kind", track['other_service_kind'][0])
            if 'default' in track:
                out += format_line("Default", track['default'])
            if 'forced' in track:
                out += format_line("Forced", track['forced'])

        elif track['track_type'] == "Text":
            out += format_line("ID", track['track_id'])
            out += format_line("Format", track['format'])
            if 'codec_id' in track:
                out += format_line("Codec ID", track['codec_id'])
            if 'codec_info' in track:
                out += format_line("Codec ID/Info", track['codec_info'])
            if 'other_duration' in track:
                out += format_line("Duration", track['other_duration'][0])
            if 'other_bit_rate' in track:
                out += format_line("Bit rate", track['other_bit_rate'][0])
            if 'count_of_elements' in track:
                out += format_line("Count of elements", track['count_of_elements'])
            if 'other_stream_size' in track:
                out += format_line("Stream size", track['other_stream_size'][0])
            if 'title' in track:
                out += format_line("Title", track['title'][0])
            if 'other_language' in track:
                out += format_line("Language", track['other_language'][0])
            if 'default' in track:
                out += format_line("Default", track['default'])
            if 'forced' in track:
                out += format_line("Forced", track['forced'])

        elif track['track_type'] in ["Menu", "Other"]:
            pass

        else:
            raise ValueError("Unknown track type: {0}".format(track['track_type']))

    return out
