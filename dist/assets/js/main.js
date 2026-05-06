/* Drive Direct — minimal client JS */

(() => {
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (!reduce && 'IntersectionObserver' in window) {
    const targets = document.querySelectorAll(
      '.hero__copy, .section__head, .services__row, .about__copy, .about__visual, .why__grid, .closing__inner'
    );
    targets.forEach(el => el.classList.add('reveal'));
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.classList.add('is-in');
          io.unobserve(e.target);
        }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -6% 0px' });
    targets.forEach(el => io.observe(el));
  }

  const nav = document.querySelector('.nav');
  if (nav) {
    const onScroll = () => nav.classList.toggle('is-scrolled', window.scrollY > 8);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  const links = document.querySelectorAll('.nav__menu a');
  const sections = [...links].map(a => document.querySelector(a.getAttribute('href'))).filter(Boolean);
  if (sections.length) {
    const spy = new IntersectionObserver((entries) => {
      entries.forEach(en => {
        if (en.isIntersecting) {
          const id = '#' + en.target.id;
          links.forEach(l => l.classList.toggle('is-active', l.getAttribute('href') === id));
        }
      });
    }, { rootMargin: '-45% 0px -50% 0px' });
    sections.forEach(s => spy.observe(s));
  }
})();
