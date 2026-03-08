import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AuthPage from "./AuthPage";

// Mock axios
vi.mock("axios", () => ({
  default: {
    post: vi.fn(),
    create: vi.fn(() => ({
      interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
    })),
  },
}));

// Mock sonner toast
vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
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
}));

// Mock lucide-react icons — use importOriginal to keep all icons available
vi.mock("lucide-react", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    BookmarkIcon: () => <span data-testid="bookmark-icon" />,
    Loader2: () => <span data-testid="loader-icon" />,
  };
});

import axios from "axios";
import { toast } from "sonner";

describe("AuthPage", () => {
  const mockOnLogin = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders login form with email and password fields", () => {
    render(<AuthPage onLogin={mockOnLogin} />);
    expect(screen.getByTestId("email-input")).toBeTruthy();
    expect(screen.getByTestId("password-input")).toBeTruthy();
  });

  it("submits login form and calls onLogin on success", async () => {
    const user = userEvent.setup();
    axios.post.mockResolvedValue({
      data: { user: { id: "1", email: "test@test.com" } },
    });

    render(<AuthPage onLogin={mockOnLogin} />);

    await user.type(screen.getByTestId("email-input"), "test@test.com");
    await user.type(screen.getByTestId("password-input"), "password123");

    const submitBtn = screen.getByTestId("auth-submit-btn");
    await user.click(submitBtn);

    await waitFor(() => {
      expect(axios.post).toHaveBeenCalledWith(
        "/api/auth/login",
        { email: "test@test.com", password: "password123" },
        { withCredentials: true },
      );
      expect(mockOnLogin).toHaveBeenCalled();
    });
  });

  it("shows error toast on login failure", async () => {
    const user = userEvent.setup();
    axios.post.mockRejectedValue({
      response: { data: { detail: "Invalid credentials" } },
    });

    render(<AuthPage onLogin={mockOnLogin} />);

    await user.type(screen.getByTestId("email-input"), "wrong@test.com");
    await user.type(screen.getByTestId("password-input"), "wrong");

    const submitBtn = screen.getByTestId("auth-submit-btn");
    await user.click(submitBtn);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith("Invalid credentials");
      expect(mockOnLogin).not.toHaveBeenCalled();
    });
  });

  it("has forgot password button", () => {
    render(<AuthPage onLogin={mockOnLogin} />);
    expect(screen.getByText(/forgot/i)).toBeTruthy();
  });
});
