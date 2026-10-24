import { describe, it, expect, vi, afterEach } from "vitest";
import { downloadReport } from "@/lib/api";

afterEach(() => vi.restoreAllMocks());

describe("downloadReport", () => {
  it("sends the bearer token and saves the file under the server's filename", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response("a,b\n", {
        status: 200,
        headers: { "Content-Disposition": 'attachment; filename="acme__api.csv"' },
      })
    );
    vi.stubGlobal("fetch", fetchMock);
    URL.createObjectURL = vi.fn(() => "blob:report");
    URL.revokeObjectURL = vi.fn();
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (
      this: HTMLAnchorElement
    ) {
      expect(this.download).toBe("acme__api.csv");
      expect(this.href).toBe("blob:report");
    });

    await downloadReport("tok-123", "rid", "csv");

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/reports\/rid\/export\?format=csv$/);
    expect(init.headers.Authorization).toBe("Bearer tok-123");
    expect(click).toHaveBeenCalledOnce();
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:report");
  });

  it("throws on a failed response instead of saving an error page", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("no", { status: 401 })));
    await expect(downloadReport("tok", "rid", "txt")).rejects.toThrow("Export failed (401)");
  });
});
