import { redirect } from "next/navigation";

export default function TermsPage() {
    redirect("/docs/terms-and-conditions.pdf");
}
