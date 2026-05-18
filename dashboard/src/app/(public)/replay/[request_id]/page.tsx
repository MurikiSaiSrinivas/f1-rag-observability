import { ReplayView } from "@/components/public/replay-view";

export default async function ReplayPage({
  params,
}: {
  params: Promise<{ request_id: string }>;
}) {
  const { request_id } = await params;
  return <ReplayView requestId={request_id} />;
}
