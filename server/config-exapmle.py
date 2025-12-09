class Config:
    # Camera(s) settings.
    #    The keys of this dictionary will be used as "camera key".
    #    Each key must contain alphanumeric [0-9a-zA-Z], UTF and some special characters [-_.*/].
    #    cameras[key] fields:
    #    * "folder" is used for the storage.
    #    * "url" must contain at least <scheme>://<host>
    #    * "codecs": RFC 6381 information about video/audio codecs (part of Media Source type),
    #       for example: "hev1.1.6.L120.0" (H.265), "avc1.42E01E, mp4a.40.2" (H.264 with audio channel).
    #    * "storage_command": can overwrite common command (set UDP mode here, enable audio channel, etc.).
    #    * "sensitivity" is used as threshold value for the Motion Detector.
    #       Must be more than 1. Set to 0 to disable.
    #    * "events": set to True if hardware Motion Detection is configured for this camera.
    #
    cameras = {
        'some-URL-compatible-string/including-UTF-characters': {
            'folder': 'some folder in the storage_path',
            'url': 'rtsp://[<login>:<password>@]<host>[:554][/<params>]',
            'codecs': '',
            'storage_command': '',
            'sensitivity': 1.5,
            'events': False,
        },
    }

    web_server_host = '0.0.0.0'
    web_server_port = 8000

    # Absolute path to VALID ssl certificates.
    # Use any service likes https://letsencrypt.org/
    # or create self-signed certificates, then import root one to your browser
    # (see README.md for details).
    # Leave blank if SSL is not required.
    ssl_certificate = ''
    ssl_private_key = ''

    # Check "storage_command" output, secs (int).
    # Used as the storage watchdog interval and motion detector one.
    min_segment_duration = 4

    # Storage video files root folder.
    # Attention!
    # All files and subdirectories older than "storage_period_days" in this folder will be deleted!
    storage_path = '/<path>'

    # Event images (motion detection) root folder.
    # Root folder for cameras FTP user must be events_path.
    # Attention!
    # All files and subdirectories older than events_period_days in this folder will be deleted!
    events_path = '/<path>'

    # {url} = cameras[key].url
    # {cam_path} = storage_path/cameras[key].folder
    # Add "-c:a aac" option here if all the cameras support audio channels.
    storage_command = (
        'ffmpeg -rtsp_transport tcp -i {url} -c:v copy -v fatal -f segment '
        '-segment_format_options movflags=frag_keyframe+empty_moov+default_base_moof '
        '-reset_timestamps 1 -strftime 1 {cam_path}/%Y-%m-%d/%H/%M/%S.mp4')

    storage_period_days = 3
    events_period_days = 30

    # Debug options
    storage_enabled = True
    events_enabled = True
    web_enabled = True
