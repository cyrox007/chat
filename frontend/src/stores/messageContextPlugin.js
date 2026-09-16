const sendActiveContext = (state) => {
	const messenger = state.messenger;
	const socket = messenger?.socket;
	if (!socket || socket.readyState !== 1 || messenger.connectionState !== 'connected') return;

	const activeDialog = messenger.activeDialog;
	if (activeDialog) {
		socket.send(JSON.stringify({
			action: 'set_active_dialog',
			other_user_uid: activeDialog,
		}));
		return;
	}

	socket.send(JSON.stringify({ action: 'clear_active_dialog' }));
};

export default (store) => {
	store.subscribe((mutation, state) => {
		if (mutation.type === 'messenger/SET_ACTIVE_DIALOG') {
			sendActiveContext(state);
			return;
		}
		if (
			mutation.type === 'messenger/SET_CONNECTION_STATE'
			&& mutation.payload === 'connected'
		) {
			sendActiveContext(state);
		}
	});
};
