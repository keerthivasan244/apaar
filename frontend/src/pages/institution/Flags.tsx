import FlagQueue from "../../components/FlagQueue";
import { Card, PageHeader } from "../../components/ui";

export default function InstitutionFlags() {
  return (
    <>
      <PageHeader title="Flags" subtitle="Issues found in your institution's records. Details of other institutions are never shown." />
      <Card>
        <FlagQueue officer={false} />
      </Card>
    </>
  );
}
