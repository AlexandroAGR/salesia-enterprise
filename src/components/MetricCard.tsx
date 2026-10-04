import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import type { ReactNode } from "react";

type MetricCardProps = {
  title: string;
  value: string;
  change: string;
  icon: ReactNode;
  color: string;
  description: string;
};

export default function MetricCard({
  title,
  value,
  change,
  icon,
  color,
  description,
}: MetricCardProps) {
  const TrendIcon = color === "orange" ? ArrowDownRight : ArrowUpRight;

  return (
    <article className="metric-card">
      <div className="metric-top">
        <span className={`metric-icon metric-${color}`}>{icon}</span>
        <span className="metric-period">Este periodo</span>
      </div>
      <p className="metric-title">{title}</p>
      <div className="metric-value-row">
        <strong>{value}</strong>
      </div>
      <div className="metric-bottom">
        <span className="metric-change">
          <TrendIcon size={14} />
          {change}
        </span>
        <span className="metric-description">{description}</span>
      </div>
    </article>
  );
}
