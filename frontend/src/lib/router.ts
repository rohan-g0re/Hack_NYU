// Route path constants
export const ROUTES = {
  HOME: '/',
  CONFIG: '/config',
  NEGOTIATIONS: '/negotiations',
  NEGOTIATION_ROOM: (roomId: string) => `/negotiations/${roomId}`,
  SUMMARY: '/summary',
} as const;

// Navigation helpers
export function getConfigPath(): string {
  return ROUTES.CONFIG;
}

export function getNegotiationsPath(): string {
  return ROUTES.NEGOTIATIONS;
}

export function getNegotiationRoomPath(roomId: string): string {
  return ROUTES.NEGOTIATION_ROOM(roomId);
}

export function getSummaryPath(): string {
  return ROUTES.SUMMARY;
}

export function getHomePath(): string {
  return ROUTES.HOME;
}

