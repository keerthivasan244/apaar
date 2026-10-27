import FlagQueue from "../../components/FlagQueue";
import { Card, PageHeader } from "../../components/ui";

export default function AicteFlags() {
  return (
    <>
      <PageHeader title="Flag queue" subtitle="Review flags across all institutions. Confirm real issues or dismiss false positives; every review is audited." />
      <Card>
        <FlagQueue officer />
      </Card>
    </>
  );
}
