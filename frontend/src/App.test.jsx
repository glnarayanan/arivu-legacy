import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import App from "./App";

// Mock axiosConfig
vi.mock("./utils/axiosConfig", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    defaults: { baseURL: "/api", withCredentials: true },
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  },
}));

// Mock framer-motion
vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }) => <div {...props}>{children}</div>,
    span: ({ children, ...props }) => <span {...props}>{children}</span>,
    button: ({ children, ...props }) => <button {...props}>{children}</button>,
    h1: ({ children, ...props }) => <h1 {...props}>{children}</h1>,
    h2: ({ children, ...props }) => <h2 {...props}>{children}</h2>,
    p: ({ children, ...props }) => <p {...props}>{children}</p>,
    form: ({ children, ...props }) => <form {...props}>{children}</form>,
  },
  AnimatePresence: ({ children }) => children,
  useAnimation: () => ({ start: vi.fn(), set: vi.fn() }),
  useInView: () => true,
}));

// Mock lucide-react
vi.mock("lucide-react", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
  };
});

// Mock sonner
vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
  Toaster: () => null,
}));

import axiosInstance from "./utils/axiosConfig";

describe("App", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows auth page when not authenticated", async () => {
    axiosInstance.get.mockRejectedValue({ response: { status: 401 } });
    render(<App />);

    await waitFor(() => {
      // Should render the auth page with email input
      expect(screen.getByTestId("email-input")).toBeTruthy();
    });
  });

  it("calls /auth/me to check authentication on mount", async () => {
    axiosInstance.get.mockRejectedValue({ response: { status: 401 } });
    render(<App />);

    await waitFor(() => {
      expect(axiosInstance.get).toHaveBeenCalledWith("/auth/me");
    });
  });
});
