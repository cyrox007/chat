import { computed, reactive } from 'vue';
import { v4 as uuidv4 } from 'uuid';
import RealtimeService from '@/API/RealtimeService';

const state = reactive({
  socket: null,
  connectionState: 'idle',
  phase: 'idle', // idle | outgoing | incoming | connecting | active | ended | error
  callUid: null,
  peerUid: null,
  peer: null,
  mode: 'audio',
  muted: false,
  cameraEnabled: true,
  localStream: null,
  remoteStream: null,
  error: null,
});

let peerConnection = null;
let heartbeatTimer = null;
let pendingCandidates = [];
let reconnectTimer = null;
let manualDisconnect = false;
const ICE_CONFIG = (() => {
  try {
    const configured = JSON.parse(import.meta.env.VITE_WEBRTC_ICE_SERVERS || '[]');
    if (Array.isArray(configured) && configured.length) return configured;
  } catch (_) { /* invalid env -> deployment warning, not app crash */ }
  return [{ urls: 'stun:stun.l.google.com:19302' }];
})();

const emitState = () => window.dispatchEvent(new CustomEvent('pubchat:call-state', { detail: { ...state } }));
const setPhase = (phase, error = null) => { state.phase = phase; state.error = error; emitState(); };

const stopHeartbeat = () => { if (heartbeatTimer) clearInterval(heartbeatTimer); heartbeatTimer = null; };
const closeSocket = () => {
  stopHeartbeat();
  if (state.socket) { try { state.socket.close(1000, 'Client disconnect'); } catch (_) {} }
  state.socket = null;
  state.connectionState = 'idle';
};

const sendSignal = (signal_type, payload = {}) => {
  if (state.socket?.readyState !== WebSocket.OPEN || !state.peerUid || !state.callUid) throw new Error('Call signaling is unavailable');
  state.socket.send(JSON.stringify({ action: signal_type, target_uid: state.peerUid, call_uid: state.callUid, ...payload }));
};

const cleanupPeer = () => {
  pendingCandidates = [];
  if (peerConnection) {
    try { peerConnection.ontrack = null; peerConnection.onicecandidate = null; peerConnection.onconnectionstatechange = null; peerConnection.close(); } catch (_) {}
  }
  peerConnection = null;
  state.localStream?.getTracks?.().forEach((track) => track.stop());
  state.remoteStream?.getTracks?.().forEach((track) => track.stop());
  state.localStream = null;
  state.remoteStream = null;
  state.muted = false;
  state.cameraEnabled = true;
};

const resetCall = () => {
  cleanupPeer();
  state.callUid = null;
  state.peerUid = null;
  state.peer = null;
  state.mode = 'audio';
  setPhase('idle');
};

const acquireMedia = async (mode) => {
  const constraints = mode === 'video'
    ? { audio: true, video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } } }
    : { audio: true, video: false };
  const stream = await navigator.mediaDevices.getUserMedia(constraints);
  state.localStream = stream;
  return stream;
};

const createPeerConnection = () => {
  if (peerConnection) return peerConnection;
  const pc = new RTCPeerConnection({ iceServers: ICE_CONFIG });
  peerConnection = pc;
  state.remoteStream = new MediaStream();
  pc.ontrack = (event) => {
    event.streams?.[0]?.getTracks()?.forEach((track) => {
      if (!state.remoteStream.getTracks().some((item) => item.id === track.id)) state.remoteStream.addTrack(track);
    });
    emitState();
  };
  pc.onicecandidate = (event) => {
    if (event.candidate) {
      try { sendSignal('call_ice', { candidate: event.candidate.toJSON ? event.candidate.toJSON() : event.candidate }); } catch (_) {}
    }
  };
  pc.onconnectionstatechange = () => {
    if (pc.connectionState === 'connected') setPhase('active');
    else if (['failed', 'disconnected'].includes(pc.connectionState) && ['active','connecting'].includes(state.phase)) setPhase('error', 'Связь прервана');
    else if (pc.connectionState === 'closed' && state.phase !== 'idle') setPhase('ended');
  };
  return pc;
};

const attachLocalTracks = (pc, stream) => stream.getTracks().forEach((track) => pc.addTrack(track, stream));
const flushCandidates = async () => {
  if (!peerConnection?.remoteDescription) return;
  const queue = pendingCandidates; pendingCandidates = [];
  for (const candidate of queue) { try { await peerConnection.addIceCandidate(candidate); } catch (_) {} }
};

const handleSignal = async (data) => {
  if (data.type !== 'call_signal') return;
  const fromUid = data.from_uid;
  if (data.signal_type === 'call_offer') {
    if (state.phase !== 'idle') {
      const previousPeer = state.peerUid; const previousCall = state.callUid;
      state.peerUid = fromUid; state.callUid = data.call_uid;
      try { sendSignal('call_decline', { reason: 'busy' }); } catch (_) {}
      state.peerUid = previousPeer; state.callUid = previousCall;
      return;
    }
    state.callUid = data.call_uid;
    state.peerUid = fromUid;
    state.peer = { uid: fromUid };
    state.mode = data.mode === 'video' ? 'video' : 'audio';
    state._incomingSdp = data.sdp;
    setPhase('incoming');
    return;
  }
  if (!state.callUid || data.call_uid !== state.callUid || fromUid !== state.peerUid) return;
  if (data.signal_type === 'call_ringing' && state.phase === 'outgoing') return;
  if (data.signal_type === 'call_answer') {
    if (!peerConnection) return;
    await peerConnection.setRemoteDescription(new RTCSessionDescription(data.sdp));
    await flushCandidates();
    setPhase('connecting');
    return;
  }
  if (data.signal_type === 'call_ice') {
    if (!peerConnection?.remoteDescription) pendingCandidates.push(data.candidate);
    else { try { await peerConnection.addIceCandidate(data.candidate); } catch (_) {} }
    return;
  }
  if (data.signal_type === 'call_decline') { cleanupPeer(); setPhase('ended', data.reason === 'busy' ? 'Пользователь занят' : 'Звонок отклонён'); return; }
  if (data.signal_type === 'call_end') { cleanupPeer(); setPhase('ended', data.reason || null); }
};

const connect = async () => {
  if (state.socket?.readyState === WebSocket.OPEN || state.connectionState === 'connecting') return;
  manualDisconnect = false;
  state.connectionState = 'connecting';
  try {
    const ticketResponse = await RealtimeService.createTicket('messenger');
    const socket = RealtimeService.openSocket('/ws/v2/calls');
    state.socket = socket;
    socket.onopen = () => {
      socket.send(JSON.stringify({ type: 'auth', ticket: ticketResponse.data.ticket }));
    };
    socket.onmessage = async (event) => {
      let data; try { data = JSON.parse(event.data); } catch (_) { return; }
      if (data.type === 'realtime_ready') {
        state.connectionState = 'connected';
        stopHeartbeat();
        heartbeatTimer = setInterval(() => { if (socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type: 'heartbeat', action: 'heartbeat' })); }, Math.max(10, data.heartbeat_seconds || 25) * 1000);
        return;
      }
      if (data.type === 'ping') { socket.send(JSON.stringify({ type: 'pong' })); return; }
      await handleSignal(data);
    };
    socket.onclose = () => {
      stopHeartbeat(); state.socket = null; state.connectionState = 'idle';
      if (!manualDisconnect) { clearTimeout(reconnectTimer); reconnectTimer = setTimeout(connect, 2000); }
    };
  } catch (error) {
    state.connectionState = 'error';
    if (!manualDisconnect) { clearTimeout(reconnectTimer); reconnectTimer = setTimeout(connect, 3000); }
  }
};

const disconnect = () => { manualDisconnect = true; clearTimeout(reconnectTimer); closeSocket(); if (state.phase !== 'idle') resetCall(); };

const start = async (peer, mode = 'audio') => {
  if (state.phase !== 'idle' && state.phase !== 'ended') throw new Error('Call already active');
  if (state.connectionState !== 'connected') await connect();
  state.callUid = uuidv4(); state.peerUid = typeof peer === 'string' ? peer : peer?.uid; state.peer = typeof peer === 'string' ? { uid: peer } : peer; state.mode = mode === 'video' ? 'video' : 'audio';
  try {
    const stream = await acquireMedia(state.mode);
    const pc = createPeerConnection(); attachLocalTracks(pc, stream);
    const offer = await pc.createOffer(); await pc.setLocalDescription(offer);
    sendSignal('call_offer', { mode: state.mode, sdp: pc.localDescription.toJSON ? pc.localDescription.toJSON() : pc.localDescription });
    setPhase('outgoing');
  } catch (error) { cleanupPeer(); setPhase('error', 'Не удалось начать звонок'); throw error; }
};

const accept = async () => {
  if (state.phase !== 'incoming' || !state._incomingSdp) return;
  try {
    const stream = await acquireMedia(state.mode);
    const pc = createPeerConnection(); attachLocalTracks(pc, stream);
    await pc.setRemoteDescription(new RTCSessionDescription(state._incomingSdp));
    await flushCandidates();
    const answer = await pc.createAnswer(); await pc.setLocalDescription(answer);
    sendSignal('call_answer', { sdp: pc.localDescription.toJSON ? pc.localDescription.toJSON() : pc.localDescription });
    delete state._incomingSdp;
    setPhase('connecting');
  } catch (error) { try { sendSignal('call_decline', { reason: 'media_unavailable' }); } catch (_) {} cleanupPeer(); setPhase('error', 'Нет доступа к камере или микрофону'); }
};
const decline = (reason = 'declined') => { try { sendSignal('call_decline', { reason }); } catch (_) {} cleanupPeer(); setPhase('ended'); };
const end = (reason = 'ended') => { try { sendSignal('call_end', { reason }); } catch (_) {} cleanupPeer(); setPhase('ended'); };
const dismiss = () => resetCall();
const toggleMute = () => { state.muted = !state.muted; state.localStream?.getAudioTracks()?.forEach((track) => { track.enabled = !state.muted; }); };
const toggleCamera = () => { state.cameraEnabled = !state.cameraEnabled; state.localStream?.getVideoTracks()?.forEach((track) => { track.enabled = state.cameraEnabled; }); };
const switchCamera = async () => {
  if (state.mode !== 'video' || !state.localStream) return;
  const current = state.localStream.getVideoTracks()[0];
  const facing = current?.getSettings?.().facingMode === 'environment' ? 'user' : 'environment';
  try {
    const replacementStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: facing }, audio: false });
    const replacement = replacementStream.getVideoTracks()[0];
    const sender = peerConnection?.getSenders?.().find((item) => item.track?.kind === 'video');
    if (sender) await sender.replaceTrack(replacement);
    if (current) { state.localStream.removeTrack(current); current.stop(); }
    state.localStream.addTrack(replacement);
    emitState();
  } catch (_) { /* leave current camera active */ }
};

export function useWebRtcCall() {
  return {
    state,
    isBusy: computed(() => state.phase !== 'idle' && state.phase !== 'ended'),
    connect, disconnect, start, accept, decline, end, dismiss, toggleMute, toggleCamera, switchCamera,
  };
}
