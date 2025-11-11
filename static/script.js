// Global frontend enhancements for BrainRush
console.log("BrainRush frontend loaded");

// Smooth scroll for internal anchor links
document.querySelectorAll('a[href^="#"]').forEach(a=>{
	a.addEventListener('click', e=>{
		const id = a.getAttribute('href').substring(1);
		const el = document.getElementById(id);
		if(el){ e.preventDefault(); el.scrollIntoView({behavior:'smooth'}); }
	});
});

// Auto-dismiss flash messages after a delay (non-error)
setTimeout(()=>{
	document.querySelectorAll('.alert').forEach(al=>{
		if(!al.classList.contains('alert-danger')){
			al.style.transition='opacity .6s ease';
			al.style.opacity='0';
			setTimeout(()=> al.remove(), 700);
		}
	});
}, 3600);

// Respect prefers-reduced-motion: strip transitions if user prefers reduced motion
if(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches){
	document.documentElement.classList.add('reduce-motion');
	const style = document.createElement('style');
	style.textContent='*{animation-duration:0.001ms !important; animation-iteration-count:1 !important; transition-duration:0.001ms !important;}';
	document.head.appendChild(style);
}

// Persist last selected topics (simple memory enhancement)
(function(){
	const boxes = document.querySelectorAll('input[name="topics"]');
	if(!boxes.length) return;
	const KEY='quiz_topics_v1';
	try{
		const saved = JSON.parse(localStorage.getItem(KEY)||'[]');
		boxes.forEach(b=>{ if(saved.includes(b.value)) b.checked=true; });
	}catch(e){}
	function store(){
		try{ const vals=[...boxes].filter(b=>b.checked).map(b=>b.value); localStorage.setItem(KEY, JSON.stringify(vals)); }catch(e){}
	}
	boxes.forEach(b=> b.addEventListener('change', store));
})();
