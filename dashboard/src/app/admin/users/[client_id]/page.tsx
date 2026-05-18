import { UserDetailView } from "@/components/admin/user-detail-view";

export default async function UserDetailPage({
  params,
}: {
  params: Promise<{ client_id: string }>;
}) {
  const { client_id } = await params;
  return <UserDetailView clientId={client_id} />;
}
