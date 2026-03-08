import { describe, it, expect } from "vitest";
import axiosInstance from "./axiosConfig";

describe("axiosConfig", () => {
  it("exports an axios instance with correct baseURL", () => {
    expect(axiosInstance.defaults.baseURL).toBe("/api");
  });

  it("has withCredentials enabled", () => {
    expect(axiosInstance.defaults.withCredentials).toBe(true);
  });

  it("sets Content-Type to application/json", () => {
    expect(axiosInstance.defaults.headers["Content-Type"]).toBe(
      "application/json",
    );
  });

  it("has request and response interceptors registered", () => {
    // Axios stores interceptors as handlers arrays
    expect(axiosInstance.interceptors.request.handlers.length).toBeGreaterThan(
      0,
    );
    expect(axiosInstance.interceptors.response.handlers.length).toBeGreaterThan(
      0,
    );
  });
});
