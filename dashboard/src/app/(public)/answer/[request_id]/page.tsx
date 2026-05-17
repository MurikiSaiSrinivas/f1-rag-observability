import { AnswerView } from "@/components/public/answer-view";

export default async function AnswerPage({
  params,
}: {
  params: Promise<{ request_id: string }>;
}) {
  const { request_id } = await params;
  return <AnswerView requestId={request_id} />;
}
