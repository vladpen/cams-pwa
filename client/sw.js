self.addEventListener('notificationclick', event => {
    event.notification.close();
    event.waitUntil(
        clients.matchAll({includeUncontrolled: true}).then(clients => {
            if (clients.length && !clients[0].focused) {
                return clients[0].focus();
            }
        })
    );
});
