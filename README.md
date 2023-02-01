## Cams PWA

![Cams](cover.jpg)

Простое веб приложение для записи и воспроизведеия RTSP потоков с IP камер в реальном времени.
Работает в браузерах на основе Chrome/Chromium не ниже 106 версии (для Linux - не ниже 108 версии)
при наличии аппаратного ускорения видео.

### Возможности:

- Запись и воспроизведение изображения c любых IP камер, включая H.265+.
- Одновременный просмотр нескольких камер.
- Увеличение изображения.
- Ускоренное воспроизведение.
- Детектор движения.
- Максимальная скорость подключения.
- Предельная простота навигации и управления.
- Крайне низкая нагрузка на процессор (транскодирование отсутствует).
- Автоматическое восстановление подключения к камерам после потери сигнала.
- Проксирование потоков с каждой камеры неограниченному количеству клиентов.
- Одно подключение к каждой камере независимо от числа клиентов.

### Требования:

Серверная часть работает на Linux с установленными python 3.7+ (без зависимостей), ffmpeg и openssl.

### Установка

Скопируйте файл конфигурации server/config-example.py в "приватный" файл server/_config.py и отредактируйте его, следуя комментариям.

Для работы PWA (прогрессивного веб приложения) требуется валидный SSL сертификат.
Для тестирования в локальной сети можно создать самозаверенный сертификат, например, так:
```bash
sudo openssl genrsa -out rootCA.key 4096
sudo openssl req -x509 -new -nodes -key rootCA.key -sha256 -days 3650 \
    -subj "/C=ХХ/L=Nsk/O=R&K/OU=R&K/CN=R&K" -out rootCA.crt
sudo chown $(whoami):$(whoami) rootCA.key
openssl genrsa -out localhost.key 2048
openssl req -new -sha256 -key localhost.key \
    -subj "/C=ХХ/L=Nsk/O=localhost/OU=localhost/CN=localhost" -out localhost.csr
openssl x509 -req -sha256 -in localhost.csr -out localhost.crt -days 3650 \
    -CAkey rootCA.key -CA rootCA.crt -CAcreateserial -extensions SAN \
    -extfile <(printf "[SAN]\nsubjectAltName=DNS:localhost,DNS:ваш-домен,IP:127.0.0.1,IP:ваш-ip")
sudo chown root:root rootCA.key
```

В этом случае корневой сертификат rootCA.crt следуедует импортировать в браузер в разделе
chrome://settings/security — Настроить сертификаты — Центры сертификации — Импорт

На мобильных устройствах корневой сертификат импортируется в разделе "Безопасность" в настройках системы.

Теперь можно запустить сервер
```bash
python3 server/main.py
```
и в браузере зайти на указанный адрес, например https://localhost:8000 (по умолчанию).

### Автоматический запуск сервера во время загрузки

Создайте юнит /etc/systemd/system/cams-pwa.service

```bash
[Unit]
Description=CAMS video monitoring

[Service]
ExecStart=/usr/bin/python3 /<path-to-cams-pwa>/server/main.py

[Install]
WantedBy=multi-user.target
```

Запустите сервис:

```bash
sudo systemctl daemon-reload
sudo systemctl enable cams-pwa
sudo systemctl start cams-pwa
```

*Copyright (c) 2023 vladpen under MIT license. Use it with absolutely no warranty.*
