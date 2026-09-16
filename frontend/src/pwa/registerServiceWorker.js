export const registerPubChatServiceWorker = async () => {
	if (!import.meta.env.PROD || !('serviceWorker' in navigator)) return null;

	try {
		const registration = await navigator.serviceWorker.register('/service-worker.js', { scope: '/' });

		registration.addEventListener('updatefound', () => {
			const worker = registration.installing;
			if (!worker) return;
			worker.addEventListener('statechange', () => {
				if (worker.state === 'installed' && navigator.serviceWorker.controller) {
					window.dispatchEvent(new CustomEvent('pubchat:app-update-ready'));
				}
			});
		});

		return registration;
	} catch (error) {
		console.warn('PubChat service worker registration failed:', error);
		return null;
	}
};
