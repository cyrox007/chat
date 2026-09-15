export const APP_VERSION = __APP_VERSION__;

const prereleaseMatch = APP_VERSION.match(/-(alpha|beta)\.(\d+)$/);

export const APP_RELEASE_CHANNEL = prereleaseMatch?.[1] || 'stable';
export const APP_RELEASE_ITERATION = prereleaseMatch ? Number(prereleaseMatch[2]) : null;

export const APP_VERSION_LABEL = APP_RELEASE_CHANNEL === 'stable'
  ? `v${APP_VERSION}`
  : `v${APP_VERSION} · ${APP_RELEASE_CHANNEL}`;
