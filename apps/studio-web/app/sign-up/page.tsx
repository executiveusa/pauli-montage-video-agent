import Link from "next/link";
import styles from "../sign-in/sign-in.module.css";

type SearchParams = Promise<{ error?: string }>;

export default async function SignUpPage({ searchParams }: { searchParams: SearchParams }) {
  const { error } = await searchParams;
  return (
    <main className={styles.page}>
      <section className={styles.brandPanel}>
        <div className={styles.orbit} aria-hidden="true" />
        <Link className={styles.brand} href="/">MONTAGE</Link>
        <div><h1 className={styles.word}>BEGIN.</h1><p className={styles.caption}>One private workspace for your footage, edit decisions, versions, and delivery evidence.</p></div>
      </section>
      <section className={styles.formPanel}>
        <div className={styles.formWrap}>
          <div className={styles.kicker}>Private beta account</div>
          <h2 className={styles.title}>Create your workspace.</h2>
          <p className={styles.copy}>Your first workspace is isolated from every other account and you become its owner.</p>
          {error ? <p className={styles.error}>{error === "conflict" ? "An account already exists for that email." : error === "service" ? "The hosted identity service is unavailable." : "Check the form and try again."}</p> : null}
          <form className={styles.form} action="/api/auth/sign-up" method="post">
            <label className={styles.label}>Name<input className={styles.input} name="displayName" autoComplete="name" required maxLength={100} /></label>
            <label className={styles.label}>Email<input className={styles.input} name="email" type="email" autoComplete="email" required /></label>
            <label className={styles.label}>Password<input className={styles.input} name="password" type="password" autoComplete="new-password" minLength={12} required /></label>
            <button className={styles.button} type="submit">Create workspace</button>
          </form>
          <Link className={styles.back} href="/sign-in">Already have an account? Sign in</Link>
        </div>
      </section>
    </main>
  );
}
