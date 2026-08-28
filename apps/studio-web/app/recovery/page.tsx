import Link from "next/link";
import styles from "../sign-in/sign-in.module.css";

type SearchParams = Promise<{ sent?: string; error?: string }>;

export default async function RecoveryPage({ searchParams }: { searchParams: SearchParams }) {
  const { sent, error } = await searchParams;
  return (
    <main className={styles.page}>
      <section className={styles.brandPanel}><Link className={styles.brand} href="/">MONTAGE</Link><div><h1 className={styles.word}>RESET.</h1><p className={styles.caption}>Recovery tokens expire after 30 minutes and can be used only once.</p></div></section>
      <section className={styles.formPanel}><div className={styles.formWrap}>
        <div className={styles.kicker}>Account recovery</div><h2 className={styles.title}>Recover access.</h2>
        <p className={styles.copy}>Enter the account email. The response stays identical whether or not an account exists.</p>
        {sent ? <p className={`${styles.error} ${styles.config}`}>If the account exists, recovery instructions have been sent through the configured delivery channel.</p> : null}
        {error ? <p className={styles.error}>Recovery is not available right now.</p> : null}
        <form className={styles.form} action="/api/auth/recovery" method="post"><label className={styles.label}>Email<input className={styles.input} name="email" type="email" autoComplete="email" required /></label><button className={styles.button} type="submit">Request recovery</button></form>
        <Link className={styles.back} href="/sign-in">← Back to sign in</Link>
      </div></section>
    </main>
  );
}
