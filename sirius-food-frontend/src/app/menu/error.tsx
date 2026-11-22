"use client";

import { useState } from "react";

export default function MenuError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const [pending, setPending] = useState(false);

  return (
    <main className="relative z-20 mx-auto max-w-3xl px-6 py-16">
      <div className="rounded-2xl border border-red-200 bg-red-50 p-8">
        <h1 className="text-2xl font-bold text-red-800">
          Не удалось загрузить меню
        </h1>
        <p className="mt-3 text-red-700">
          Проверьте, что бэкенд запущен на http://127.0.0.1:8000
        </p>
        <p className="mt-2 text-sm text-red-600">{error.message}</p>
        <button
          type="button"
          disabled={pending}
          onClick={() => {
            setPending(true);
            reset();
          }}
          className="mt-6 cursor-pointer rounded-xl bg-red-700 px-5 py-2.5 font-semibold text-white hover:bg-red-800 active:bg-red-900 disabled:cursor-wait"
        >
          {pending ? "Пробуем ещё раз…" : "Попробовать снова"}
        </button>
      </div>
    </main>
  );
}