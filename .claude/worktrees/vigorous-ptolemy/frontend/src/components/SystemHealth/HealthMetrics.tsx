import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { motion } from 'framer-motion';
import { Clock, Users, Timer, Activity } from 'lucide-react';

interface MetricProps {
  label: string;
  value: string;
  subtitle: string;
  icon: React.ReactNode;
  color: string;
  bgColor: string;
  gauge?: number;
}

function AnimatedNumber({ target, suffix = '' }: { target: string; suffix?: string }) {
  const numericPart = parseFloat(target.replace(/[^0-9.]/g, ''));
  const prefix = target.replace(/[0-9.KkMm%]+/g, '').trim();
  const [current, setCurrent] = useState(0);

  useEffect(() => {
    const duration = 1200;
    const steps = 40;
    const increment = numericPart / steps;
    let step = 0;
    const timer = setInterval(() => {
      step++;
      setCurrent(step >= steps ? numericPart : increment * step);
      if (step >= steps) clearInterval(timer);
    }, duration / steps);
    return () => clearInterval(timer);
  }, [numericPart]);

  const formatted = target.includes('K')
    ? `${Math.round(current)}K`
    : target.includes('%')
    ? `${current.toFixed(1)}%`
    : current.toFixed(1);

  return (
    <span>
      {prefix}
      {formatted}
      {suffix}
    </span>
  );
}

function GaugeRing({ value, color }: { value: number; color: string }) {
  const radius = 36;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value / 100) * circumference;

  return (
    <svg width="88" height="88" className="mx-auto">
      <circle cx="44" cy="44" r={radius} fill="none" stroke="currentColor" strokeWidth="6" className="text-muted/30" />
      <motion.circle
        cx="44"
        cy="44"
        r={radius}
        fill="none"
        stroke={color}
        strokeWidth="6"
        strokeLinecap="round"
        strokeDasharray={circumference}
        initial={{ strokeDashoffset: circumference }}
        animate={{ strokeDashoffset: offset }}
        transition={{ duration: 1.2, ease: 'easeOut' }}
        transform="rotate(-90 44 44)"
      />
      <text x="44" y="48" textAnchor="middle" className="fill-foreground text-sm font-bold">
        {Math.round(value)}%
      </text>
    </svg>
  );
}

function MetricCard({ label, value, subtitle, icon, color, bgColor, gauge }: MetricProps) {
  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
      <Card className="relative overflow-hidden border border-border/30 shadow-md hover:shadow-lg hover:border-border/60 transition-all duration-200 rounded-lg">
        <div className={`absolute inset-0 ${bgColor} opacity-[0.07]`} />
        <CardContent className="p-5 relative">
          <div className="flex items-start justify-between mb-3">
            <div className={`p-2.5 rounded-xl ${bgColor} bg-opacity-15`}>{icon}</div>
            <div className="flex items-center gap-1.5">
              <span className="relative flex h-2.5 w-2.5">
                <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${bgColor} opacity-60`} />
                <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${bgColor}`} />
              </span>
              <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Live</span>
            </div>
          </div>
          {gauge !== undefined ? (
            <div className="flex flex-col items-center">
              <GaugeRing value={gauge} color={color} />
              <p className="text-xs font-medium text-muted-foreground mt-2">{label}</p>
              <p className="text-[10px] text-muted-foreground">{subtitle}</p>
            </div>
          ) : (
            <>
              <p className="text-3xl font-bold tracking-tight tabular-nums" style={{ color }}>
                <AnimatedNumber target={value} />
              </p>
              <p className="text-sm font-medium mt-1">{label}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>
            </>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}

export function HealthMetrics() {
  const metrics: MetricProps[] = [
    {
      label: 'On-Time Performance',
      value: '94.2%',
      subtitle: '+1.3% vs last week',
      icon: <Clock className="h-5 w-5 text-emerald-600" />,
      color: '#059669',
      bgColor: 'bg-emerald-500',
    },
    {
      label: 'Daily Ridership',
      value: '142K',
      subtitle: 'Across all 4 rail lines',
      icon: <Users className="h-5 w-5 text-blue-600" />,
      color: '#2563EB',
      bgColor: 'bg-blue-500',
    },
    {
      label: 'Avg Wait Time',
      value: '4.2',
      subtitle: 'Minutes between trains',
      icon: <Timer className="h-5 w-5 text-amber-600" />,
      color: '#D97706',
      bgColor: 'bg-amber-500',
    },
    {
      label: 'System Load',
      value: '72%',
      subtitle: 'Current capacity utilization',
      icon: <Activity className="h-5 w-5 text-purple-600" />,
      color: '#7C3AED',
      bgColor: 'bg-purple-500',
      gauge: 72,
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {metrics.map((m, i) => (
        <MetricCard key={i} {...m} />
      ))}
    </div>
  );
}
