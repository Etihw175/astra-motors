// เอฟเฟกต์ประกอบฉาก (ตกแต่งอย่างเดียว ไม่กระทบการทำงานหลัก):
// scroll reveal, การ์ดเอียงตามเมาส์+ไฮไลต์วิ่งตาม, ตัวเลขวิ่ง (count-up)
"use strict";

const FX = (() => {
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ค่อยๆ เผยหัวข้อ/ขั้นตอนเมื่อเลื่อนถึง
  function initReveal() {
    if (reduceMotion || !("IntersectionObserver" in window)) return;
    const els = document.querySelectorAll(".jstep, .section-head");
    els.forEach((el, i) => {
      el.classList.add("reveal");
      el.style.transitionDelay = `${(i % 4) * 80}ms`;
    });
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add("in");
            io.unobserve(e.target);
          }
        });
      },
      { threshold: 0.15 }
    );
    els.forEach((el) => io.observe(el));
  }

  // การ์ดเอียงตาม 3 มิติ + จุดไฮไลต์ทองแดงวิ่งตามเมาส์ (ปิดบนจอสัมผัส)
  function bindCardFX(scope = document) {
    if (window.matchMedia("(pointer: coarse)").matches) return;
    scope.querySelectorAll(".car-card").forEach((card) => {
      if (card.dataset.fx) return;
      card.dataset.fx = "1";
      card.addEventListener("pointermove", (e) => {
        const r = card.getBoundingClientRect();
        const x = e.clientX - r.left;
        const y = e.clientY - r.top;
        card.style.setProperty("--mx", `${x}px`);
        card.style.setProperty("--my", `${y}px`);
        if (!reduceMotion) {
          const rx = (y / r.height - 0.5) * -5;
          const ry = (x / r.width - 0.5) * 7;
          card.style.transform =
            `perspective(900px) rotateX(${rx}deg) rotateY(${ry}deg) translateY(-4px)`;
        }
      });
      card.addEventListener("pointerleave", () => {
        card.style.transform = "";
      });
    });
  }

  // ตัวเลขวิ่งจาก 0 ไปค่าจริง (ease-out)
  function countUp(el, target, duration = 1100) {
    if (!el) return;
    const isFloat = !Number.isInteger(target);
    if (reduceMotion) {
      el.textContent = isFloat ? target.toFixed(1) : target.toLocaleString("th-TH");
      return;
    }
    const start = performance.now();
    function frame(now) {
      const p = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      const val = target * eased;
      el.textContent = isFloat ? val.toFixed(1) : Math.round(val).toLocaleString("th-TH");
      if (p < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  initReveal();
  return { bindCardFX, countUp };
})();
