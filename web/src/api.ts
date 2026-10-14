let csrf = "";
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}
export function setCsrf(value: string) {
  csrf = value;
}
export async function api<T = any>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const response = await fetch("/api" + path, {
    method,
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      ...(method === "GET" ? {} : { "X-CSRF-Token": csrf }),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await response
    .json()
    .catch(() => ({ error: "服务返回了非 JSON 响应" }));
  if (!response.ok) {
    const detail = data.detail;
    throw new ApiError(
      data.error ||
        (Array.isArray(detail)
          ? detail.map((v: any) => v.msg).join("；")
          : detail) ||
        `请求失败 (${response.status})`,
      response.status,
    );
  }
  return data;
}
