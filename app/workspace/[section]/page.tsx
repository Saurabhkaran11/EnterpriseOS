import { notFound } from "next/navigation";
import { Workspace } from "../Workspace";

const valid = ["inbox", "crm", "tasks", "calendar", "report"];

export default async function WorkspacePage({ params }: { params: Promise<{ section: string }> }) {
  const { section } = await params;
  if (!valid.includes(section)) notFound();
  return <Workspace section={section} />;
}
