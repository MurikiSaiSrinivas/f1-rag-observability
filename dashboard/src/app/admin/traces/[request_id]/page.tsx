import { TraceDetailView } from "@/components/admin/trace-detail-view";

export default async function TraceDetailPage({
  params,
}: {
  params: Promise<{ request_id: string }>;
}) {
  const { request_id } = await params;
  return <TraceDetailView requestId={request_id} />;
}
