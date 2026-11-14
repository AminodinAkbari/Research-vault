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
          borderRadius: "102px",
          color: "#ffffff",
          fontSize: "234px",
          fontWeight: 700,
          fontFamily: "sans-serif",
          letterSpacing: "-6px",
        }}
      >
        RV
      </div>
    ),
    {
      width: 512,
      height: 512,
    }
  );
}
