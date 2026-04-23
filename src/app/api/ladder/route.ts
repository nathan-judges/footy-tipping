import { loadLadder } from "@/lib/loadTips";

export const runtime = "edge";

export async function GET() {
  return Response.json(loadLadder());
}
