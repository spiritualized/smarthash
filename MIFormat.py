def MIFormatLine(k, v):
	return "{0}: {1}\n".format(k.ljust(41), v)

def MItostring(mediainfo):

	out = ""

	for track in mediainfo:
		if 'text_format_list' in track:
			continue
		if track.get('format') == "RLE":
			continue

		#for k,v in track.items():
		#	print(MIFormatLine(k,v), end="")

		if out != "":
			out += "\n"

		out += track['track_type']+"\n"

		if track['track_type'] == "General":
			if 'unique_id' in track:
				out += MIFormatLine("Unique ID", track['unique_id'])
			out += MIFormatLine("Complete name", track['complete_name'])
			out += MIFormatLine("Format", track['format'])
			if 'format_info' in track:
				out += MIFormatLine("Format/Info", track['format_info'])
			if 'format_version' in track:
				out += MIFormatLine("Format version", track['format_version'])
			out += MIFormatLine("File size", track['other_file_size'][0])
			out += MIFormatLine("Duration", track['other_duration'][0])
			if 'other_overall_bit_rate_mode' in track:
				out += MIFormatLine("Overall bit rate mode", track['other_overall_bit_rate_mode'][0])
			out += MIFormatLine("Overall bit rate", track['other_overall_bit_rate'][0])
			if 'encoded_date' in track:
				out += MIFormatLine("Encoded date", track['encoded_date'])
			if 'writing_application' in track:
				out += MIFormatLine("Writing application", track['writing_application'])
			if 'writing_library' in track:
				out += MIFormatLine("Writing library", track['writing_library'])
		
		elif track['track_type'] == "Video":

			out += MIFormatLine("ID", track['track_id'])
			out += MIFormatLine("Format", track['format'])
			if 'format_info' in track:
				out += MIFormatLine("Format/Info", track['format_info'])
			if 'format_profile' in track:
				out += MIFormatLine("Format profile", track['format_profile'])
			if 'format_settings' in track:
				out += MIFormatLine("Format settings", track['format_settings'])
			if 'format_settings__bvop' in track:
				out += MIFormatLine("Format settings, BVOP", track['format_settings__bvop'])
			if 'format_settings__qpel' in track:
				out += MIFormatLine("Format settings, QPel", track['format_settings__qpel'])
			if 'format_settings__gmc' in track:
				out += MIFormatLine("Format settings, GMC", track['format_settings__gmc'])
			if 'format_settings__matrix' in track:
				out += MIFormatLine("Format settings, Matrix", track['format_settings__matrix'])
			if 'codec_settings__cabac' in track:
				out += MIFormatLine("Format settings, CABAC", track['codec_settings__cabac'])
			if 'codec_settings_refframes' in track:
				out += MIFormatLine("Format settings, RefFrames", track['codec_settings_refframes'])
			if 'muxing_mode' in track:
				out += MIFormatLine("Muxing mode", track['muxing_mode'])
			out += MIFormatLine("Codec ID", track['codec_id'])
			if 'codec_id_hint' in track:
				out += MIFormatLine("Codec ID/Hint", track['codec_id_hint'])
			if 'other_duration' in track:
				out += MIFormatLine("Duration", track['other_duration'][0])
			if 'other_bit_rate_mode' in track:
				out += MIFormatLine("Bit rate mode", track['other_bit_rate_mode'][0])
			if 'other_bit_rate' in track:
				out += MIFormatLine("Bit rate", track['other_bit_rate'][0])
			if 'other_maximum_bit_rate' in track:
				out += MIFormatLine("Maximum bit rate", track['other_maximum_bit_rate'][0])
			if 'overall_bit_rate_mode' in track:
				out += MIFormatLine("Overall bit rate mode", track['overall_bit_rate_mode'][0])
			if 'overall_bit_rate' in track:
				out += MIFormatLine("Overall bit rate", track['overall_bit_rate'][0])
			out += MIFormatLine("Width", track['other_width'][0])
			out += MIFormatLine("Height", track['other_height'][0])
			out += MIFormatLine("Display aspect ratio", track['other_display_aspect_ratio'][0])
			if 'other_frame_rate_mode' in track:
				out += MIFormatLine("Frame rate mode", track['other_frame_rate_mode'][0])
			if 'other_frame_rate' in track:
				out += MIFormatLine("Frame rate", track['other_frame_rate'][0])
			if 'other_original_frame_rate' in track:
				out += MIFormatLine("Frame rate mode", track['other_original_frame_rate'][0])
			out += MIFormatLine("Color space", track['color_space'])
			if 'chroma_subsampling' in track:
				out += MIFormatLine("Chroma subsampling", track['chroma_subsampling'])
			out += MIFormatLine("Bit depth", track['other_bit_depth'][0])
			if 'scan_type' in track:
				out += MIFormatLine("Scan type", track['scan_type'])
			if 'compression_mode' in track:
				out += MIFormatLine("Compression mode", track['compression_mode'])
			if 'bits__pixel_frame' in track:
				out += MIFormatLine("Bits/(Pixel*Frame)", track['bits__pixel_frame'])
			if 'other_stream_size' in track:
				out += MIFormatLine("Stream size", track['other_stream_size'][0])
			if 'other_writing_library' in track:
				out += MIFormatLine("Writing library", track['other_writing_library'][0])
			if 'encoding_settings' in track:
				out += MIFormatLine("Encoding settings", track['encoding_settings'])
			if 'other_language' in track:
				out += MIFormatLine("Language", track['other_language'][0])
			if 'default' in track:
				out += MIFormatLine("Default", track['default'])
			if 'forced' in track:
				out += MIFormatLine("Forced", track['forced'])
			if 'color_range' in track:
				out += MIFormatLine("Color range", track['color_range'])
			if 'color_primaries' in track:
				out += MIFormatLine("Color primaries", track['color_primaries'])
			if 'transfer_characteristics' in track:
				out += MIFormatLine("Transfer characteristics", track['transfer_characteristics'])
			if 'matrix_coefficients' in track:
				out += MIFormatLine("Matrix coefficients", track['matrix_coefficients'])


		elif track['track_type'] == "Audio":

			out += MIFormatLine("ID", track['track_id'])
			out += MIFormatLine("Format", track['format'])
			if 'format_version' in track:
				out += MIFormatLine("Format version", track['format_version'])
			if 'format_profile' in track:
				out += MIFormatLine("Format profile", track['format_profile'])
			if 'format_settings' in track:
				out += MIFormatLine("Format settings", track['format_settings'])
			if 'format_info' in track:
				out += MIFormatLine("Format/Info", track['format_info'])
			out += MIFormatLine("Codec ID", track['codec_id'])
			if 'codec_id_hint' in track:
				out += MIFormatLine("Codec ID/Hint", track['codec_id_hint'])
			if 'other_duration' in track:
				out += MIFormatLine("Duration", track['other_duration'][0])
			if 'other_bit_rate_mode' in track:
				out += MIFormatLine("Bit rate mode", track['other_bit_rate_mode'][0])
			if 'other_bit_rate' in track:
				out += MIFormatLine("Bit rate", track['other_bit_rate'][0])
			if 'other_minimum_bit_rate' in track:
				out += MIFormatLine("Minimum bit rate", track['other_minimum_bit_rate'][0])
			out += MIFormatLine("Channel(s)", track['other_channel_s'][0])
			if 'channel_positions' in track:
				out += MIFormatLine("Channel positions", track['channel_positions'])
			out += MIFormatLine("Sampling rate", track['other_sampling_rate'][0])
			if 'other_frame_rate' in track:
				out += MIFormatLine("Frame rate", track['other_frame_rate'][0])
			if 'other_compression_mode' in track:
				out += MIFormatLine("Compression mode", track['other_compression_mode'][0])
			if 'other_stream_size' in track:
				out += MIFormatLine("Stream size", track['other_stream_size'][0])
			if 'other_alignment' in track:
				out += MIFormatLine("Alignment", track['other_alignment'][0])
			if 'other_interleave__duration' in track:
				out += MIFormatLine("Interleave, duration", track['other_interleave__duration'][1])
			if 'other_interleave__preload_duration' in track:
				out += MIFormatLine("Interleave, preload duration", track['other_interleave__preload_duration'][0])
			if 'writing_library' in track:
				out += MIFormatLine("Writing library", track['writing_library'])
			if 'encoding_settings' in track:
				out += MIFormatLine("Encoding settings", track['encoding_settings'])
			if 'other_language' in track:
				out += MIFormatLine("Language", track['other_language'][0])
			if 'other_service_kind' in track:
				out += MIFormatLine("Service kind", track['other_service_kind'][0])
			if 'default' in track:
				out += MIFormatLine("Default", track['default'])
			if 'forced' in track:
				out += MIFormatLine("Forced", track['forced'])

		elif track['track_type'] == "Text":
			out += MIFormatLine("ID", track['track_id'])
			out += MIFormatLine("Format", track['format'])
			out += MIFormatLine("Codec ID", track['codec_id'])
			out += MIFormatLine("Codec ID/Info", track['codec_info'])
			if 'other_duration' in track:
				out += MIFormatLine("Duration", track['other_duration'][0])
			if 'other_bit_rate' in track:
				out += MIFormatLine("Bit rate", track['other_bit_rate'][0])
			if 'count_of_elements' in track:
				out += MIFormatLine("Count of elements", track['count_of_elements'])
			if 'other_stream_size' in track:
				out += MIFormatLine("Stream size", track['other_stream_size'][0])
			if 'title' in track:
				out += MIFormatLine("Title", track['title'][0])
			if 'other_language' in track:
				out += MIFormatLine("Language", track['other_language'][0])
			out += MIFormatLine("Default", track['default'])
			out += MIFormatLine("Forced", track['forced'])

		elif track['track_type'] == "Menu":
			pass

		else:
			raise ValueError("Unknown track type: {0}".format(track['track_type']))

	return out