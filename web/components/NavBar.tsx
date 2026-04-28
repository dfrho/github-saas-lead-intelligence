"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase";

export function NavBar() {
  const router = useRouter();
  const [email, setEmail] = useState<string | null>(null);

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getSession().then(({ data: { session } }) => {
      setEmail(session?.user?.email ?? null);
    });
  }, []);

  async function handleSignOut() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/");
  }

  return (
    <nav className="border-b border-gray-200 bg-white px-4 py-3">
      <div className="max-w-5xl mx-auto flex items-center justify-between">
        <a href="/dashboard" className="text-sm font-semibold text-gray-900 hover:text-gray-700">
          Repolytics
        </a>
        <div className="flex items-center gap-4 text-sm text-gray-500">
          {email && <span className="hidden sm:inline">{email}</span>}
          <a href="/account" className="hover:text-gray-900 transition-colors">Account</a>
          <button
            onClick={handleSignOut}
            className="hover:text-gray-900 transition-colors"
          >
            Sign out
          </button>
        </div>
      </div>
    </nav>
  );
}
