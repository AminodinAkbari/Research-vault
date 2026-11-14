import { ImageResponse } from "next/og";

export const runtime = "edge";

export async function GET() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: "#2563eb",
          borderRadius: "38px",
          color: "#ffffff",
          fontSize: "88px",
          fontWeight: 700,
          fontFamily: "sans-serif",
          letterSpacing: "-2px",
        }}
      >
        RV
      </div>
    ),
    {
      width: 192,
      height: 192,
    }
  );
}
