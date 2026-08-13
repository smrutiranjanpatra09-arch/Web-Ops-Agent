import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { useHealth } from "../api/queries";

export default function SystemHealth() {
  const { data } = useHealth();

  return (
    <div className="mx-auto max-w-2xl p-8">
      <h1 className="text-xl font-bold">System health</h1>
      <Card className="mt-4">
        <CardHeader><CardTitle>Services</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {data && Object.entries(data.services).map(([name, status]) => (
            <div key={name} className="flex items-center justify-between border-b border-border py-2 text-sm last:border-0">
              <span className="font-mono">{name}</span>
              <Badge variant={status === "healthy" ? "success" : "destructive"}>{status}</Badge>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
