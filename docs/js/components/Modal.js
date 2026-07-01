export function showModal(title, contentHtml) {
    const overlay = document.getElementById('app-modal');
    const titleEl = document.getElementById('modal-title');
    const bodyEl = document.getElementById('modal-body');
    
    titleEl.textContent = title;
    bodyEl.innerHTML = contentHtml;
    
    overlay.classList.add('active');
}

export function hideModal() {
    const overlay = document.getElementById('app-modal');
    overlay.classList.remove('active');
    setTimeout(() => {
        document.getElementById('modal-body').innerHTML = '';
    }, 300);
}

export function initModal() {
    const overlay = document.getElementById('app-modal');
    const closeBtn = document.getElementById('modal-close');
    
    closeBtn.addEventListener('click', hideModal);
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) hideModal();
    });
}
