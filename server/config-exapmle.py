class Config:
    # Camera(s) settings.
    #    The keys of this dictionary will be called "camera hash".
    #    * "folder" is used for the storage.
    #    * "url" must contain at least <protocol>://<host>
    #    * "name" is just visible camera name, can include emoji
    #    * "codecs": RFC 6381 information about video/audio codecs (part of Media Source type),
    #       for example: "hev1.1.6.L120.0" (H.265), "avc1.42E01E, mp4a.40.2" (H.264 with audio channel)
    #    * "storage_command": can owerwrite common command (set UDP mode here, enable audio channel, etc.)
    #    * "sensitivity" is used as threasold value for the Motion Detector.
    #       Must be more than 1. Set to 0 to disable.
    #
    cameras = {
        'some-URL-compatible-string/including-UTF-characters': {
            'folder': 'some folder in the storage_path',
            'url': 'rtsp://[<login>:<password>@]<host>[:554][/<params>]',
            'name': 'Any camera name',
            'codecs': '',
            'storage_command': '',
            'sensitivity': 1.5,
            'events': False,
        },
    }

    # Temporary group settings
    groups = {
        'grp1': {
            'cams': ['camera-hash'],
            'name': '❄️ Group 1',
        }
    }

    # Home page title
    title = 'Cams'
    # PWA title.
    # Useful for multiple app instances accessed over a local network and the web
    web_title = 'Cams'

    web_server_host = '0.0.0.0'
    web_server_port = 8000
    web_server_name = 'Cams PWA'

    master_cam_hash = 'master cam hash'
    # Use hashlib.sha256(b"my_secret_password").hexdigest() to encode "my_secret_password"
    # default is "1234"
    master_password_hash = '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4'
    # default is "1111"
    cam_password_hash = '0ffe1abd1a08215353c233d6e009613e95eec4253832a761af28ff37ac5a150c'
    encryption_key = 'Secret Encryption Key'

    # Path to VALID ssl certificates.
    # Use any service likes https://letsencrypt.org/
    # or create self-signed certificate, then import root one to your browser.
    ssl_certificate = '/<path>/_localhost.crt'
    ssl_private_key = '/<path>/_localhost.key'

    # Check "storage_command" output, secs (int).
    # Used as the storage watchdog interval and motion detector interval
    min_segment_duration = 4

    # Run this script with root permissions or set up log rotation yourself
    log_file = '/var/log/cams-pwa.log'

    # Attention!
    # All files and subdirectories older than "storage_period_days" in this folder will be deleted!
    storage_path = '/<path>'

    # {url} = cameras.hash.url
    # {cam_path} = storage_path/cameras.hash.folder
    # Add "-c:a aac" option here if all the cameras support audio channels
    storage_command = (
        'ffmpeg -rtsp_transport tcp -i {url} -c:v copy -v fatal -f segment '
        '-segment_format_options movflags=frag_keyframe+empty_moov+default_base_moof '
        '-reset_timestamps 1 -strftime 1 {cam_path}/%Y-%m-%d/%H/%M/%S.mp4')

    storage_period_days = 3

    # Root folder for FTP user
    events_path = '/<path>'

    events_period_days = 30

    # Debug options
    debug = False
    storage_enabled = True
    events_enabled = True
    web_enabled = True
