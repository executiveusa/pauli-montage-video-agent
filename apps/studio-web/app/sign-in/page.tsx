import Link from "next/link";
import styles from "./sign-in.module.css";

type SearchParams = Promise<{ error?: string }>;

export default async function SignInPage({ searchParams }: { searchParams: SearchParams }) {
  const { error } = await searchParams;
  const configurationError = error === "configuration";
  const credentialError = error === "credentials";
  const serviceError = error === "service";

  return (
    <main className={styles.page}>
      <section className={styles.brandPanel}>
        <div className={styles.orbit} aria-hidden="true" />
        <Link className={styles.brand} href="/">MONTAGE</Link>
        <div>
          <h1 className={styles.word}>CUT.</h1>
          <p className={styles.caption}>Your footage, project history, edit decisions, and exports stay behind an owner-controlled studio session.</p>
        </div>
      </section>
      <section className={styles.formPanel}>
        <div className={styles.formWrap}>
          <div className={styles.kicker}>Test Montage</div>
          <h2 className={styles.title}>Start editing.</h2>
          <p className={styles.copy}>Open the browser-local workspace without an email or password. Create a project, try the timeline, and review the local editing flow.</p>
          <Link className={styles.button} href="/studio">Open local workspace →</Link>
          <p className={styles.copy}>Local projects stay in this browser. Hosted projects, private cloud footage, and protected production actions still require owner access. This is not a shared production account.</p>
          <details>
            <summary>Owner sign-in</summary>
            {configurationError ? (
              <p className={`${styles.error} ${styles.config}`}>Studio access is intentionally locked because production credentials are not configured. Set MONTAGE_OWNER_EMAIL, MONTAGE_OWNER_PASSWORD_HASH (or MONTAGE_OWNER_PASSWORD), and a 32+ character MONTAGE_SESSION_SECRET.</p>
            ) : null}
            {credentialError ? <p className={styles.error}>That email and password did not match the configured studio owner.</p> : null}
            {serviceError ? <p className={styles.error}>The hosted identity service could not be reached. Your credentials were not stored by this page.</p> : null}
            <form className={styles.form} action="/api/auth/sign-in" method="post">
              <label className={styles.label}>Email<input className={styles.input} name="email" type="email" autoComplete="email" required /></label>
              <label className={styles.label}>Password<input className={styles.input} name="password" type="password" autoComplete="current-password" required /></label>
              <button className={styles.button} type="submit">Enter owner studio</button>
            </form>
            <div className={styles.accountLinks}><Link href="/sign-up">Create an account</Link><Link href="/recovery">Forgot password?</Link></div>
          </details>
          <Link className={styles.back} href="/">← Back to the landing page</Link>
        </div>
      </section>
    </main>
  );
}
