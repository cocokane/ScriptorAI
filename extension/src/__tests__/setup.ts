/**
 * Jest test setup
 */
import '@testing-library/jest-dom';

// Mock chrome API
const chromeMock = {
  runtime: {
    sendMessage: jest.fn(),
    onMessage: { addListener: jest.fn() },
    getURL: jest.fn((path: string) => `chrome-extension://test/${path}`),
    onInstalled: { addListener: jest.fn() },
  },
  storage: {
    local: {
      get: jest.fn().mockResolvedValue({}),
      set: jest.fn().mockResolvedValue(undefined),
      remove: jest.fn().mockResolvedValue(undefined),
    },
  },
  tabs: {
    query: jest.fn().mockResolvedValue([]),
    create: jest.fn().mockResolvedValue({ id: 1 }),
  },
  sidePanel: {
    open: jest.fn().mockResolvedValue(undefined),
    setPanelBehavior: jest.fn().mockResolvedValue(undefined),
  },
  contextMenus: {
    create: jest.fn(),
    onClicked: { addListener: jest.fn() },
  },
  commands: {
    onCommand: { addListener: jest.fn() },
  },
  action: {
    onClicked: { addListener: jest.fn() },
  },
  notifications: {
    create: jest.fn(),
  },
};

// @ts-ignore
global.chrome = chromeMock;

// Mock fetch
global.fetch = jest.fn();

// Reset mocks before each test
beforeEach(() => {
  jest.clearAllMocks();
});
