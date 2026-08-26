"use client";

import * as React from "react";
import Link from "next/link";
import { Menu, ShieldCheck, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { useAuth } from "@/hooks/use-auth";

export function Navbar() {
  const { user, isLoading, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = React.useState(false);

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/80 backdrop-blur">
      <div className="container flex h-16 items-center justify-between px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight text-foreground">
          <ShieldCheck className="h-5 w-5 text-primary" aria-hidden />
          TrustBuy AI
        </Link>

        {/* Desktop Navigation */}
        <nav className="hidden items-center gap-2 md:flex">
          <Button variant="ghost" asChild>
            <Link href="/leaderboard">Leaderboard</Link>
          </Button>
          <ThemeToggle />
          {isLoading ? null : user ? (
            <>
              <Button variant="ghost" asChild>
                <Link href="/dashboard">Dashboard</Link>
              </Button>
              <Button variant="outline" onClick={() => logout()}>
                Log out
              </Button>
            </>
          ) : (
            <>
              <Button variant="ghost" asChild>
                <Link href="/login">Sign in</Link>
              </Button>
              <Button asChild>
                <Link href="/signup">Get Started</Link>
              </Button>
            </>
          )}
        </nav>

        {/* Mobile Navigation Controls */}
        <div className="flex items-center gap-2 md:hidden">
          <ThemeToggle />
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setMobileOpen((prev) => !prev)}
            aria-label={mobileOpen ? "Close menu" : "Open menu"}
          >
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </Button>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {mobileOpen && (
        <div className="border-b border-border bg-background px-4 pb-6 pt-3 shadow-lg md:hidden">
          <nav className="flex flex-col gap-2">
            <Button variant="ghost" asChild className="justify-start text-base" onClick={() => setMobileOpen(false)}>
              <Link href="/leaderboard">Leaderboard</Link>
            </Button>
            {isLoading ? null : user ? (
              <>
                <Button variant="ghost" asChild className="justify-start text-base" onClick={() => setMobileOpen(false)}>
                  <Link href="/dashboard">Dashboard</Link>
                </Button>
                <Button
                  variant="outline"
                  className="justify-start text-base"
                  onClick={() => {
                    setMobileOpen(false);
                    logout();
                  }}
                >
                  Log out
                </Button>
              </>
            ) : (
              <>
                <Button variant="ghost" asChild className="justify-start text-base" onClick={() => setMobileOpen(false)}>
                  <Link href="/login">Sign in</Link>
                </Button>
                <Button asChild className="justify-start text-base" onClick={() => setMobileOpen(false)}>
                  <Link href="/signup">Get Started</Link>
                </Button>
              </>
            )}
          </nav>
        </div>
      )}
    </header>
  );
}
