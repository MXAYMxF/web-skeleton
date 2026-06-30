'use client';

import { useEffect, useState } from 'react';
import api from '@/utils/api';

// The backend URL is configured in .env (NEXT_PUBLIC_API_URL), not hardcoded
// here — so the running app always shows which API it is wired to.
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? '(same origin)';

interface Health {
  app: string;
  status: string;
  version: string;
  database: string;
  environment: string;
}

type State =
  | { kind: 'loading' }
  | { kind: 'ok'; health: Health }
  | { kind: 'error' };

/**
 * Live API connection indicator: shows the configured backend URL and a
 * health dot driven by GET /api/v1/health. Surfaces the front-end ↔ API link
 * in the running app instead of hiding it in config files.
 */
export default function ApiStatus() {
  const [state, setState] = useState<State>({ kind: 'loading' });

  useEffect(() => {
    let active = true;
    api
      .get<Health>('/health')
      .then((res) => {
        if (active) setState({ kind: 'ok', health: res.data });
      })
      .catch(() => {
        if (active) setState({ kind: 'error' });
      });
    return () => {
      active = false;
    };
  }, []);

  const connected = state.kind === 'ok' && state.health.status === 'healthy';
  const dotColor =
    state.kind === 'loading'
      ? 'bg-gray-300'
      : connected
        ? 'bg-green-500'
        : 'bg-red-500';
  const label =
    state.kind === 'loading'
      ? 'Checking API…'
      : connected
        ? 'API connected'
        : 'API unreachable';

  const title =
    state.kind === 'ok'
      ? `${state.health.app} • database: ${state.health.database} • environment: ${state.health.environment}`
      : `Backend: ${API_URL}`;

  return (
    <span className="inline-flex items-center gap-1.5" title={title}>
      <span
        className={`inline-block h-2 w-2 rounded-full ${dotColor}`}
        aria-hidden="true"
      />
      <span>{label}</span>
      <span className="text-gray-400">·</span>
      <span className="font-mono text-xs">{API_URL}</span>
      {state.kind === 'ok' && (
        <>
          <span className="text-gray-400">·</span>
          <span>v{state.health.version}</span>
          <span className="text-gray-400">·</span>
          <span>{state.health.environment}</span>
        </>
      )}
    </span>
  );
}
