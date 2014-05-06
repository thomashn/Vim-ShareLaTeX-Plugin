
let g:nothing=""
function Sharelatex()
	let g:cmd="start"
	pyfile git/Vim-ShareLaTex-Plugin/client.py
endfunction

function Sharelatex_project_up()
	let g:cmd="up"
	pyfile git/Vim-ShareLaTex-Plugin/client.py
endfunction

function Sharelatex_project_down()
	let g:cmd="down"
	pyfile git/Vim-ShareLaTex-Plugin/client.py
endfunction

function Sharelatex_project_enter()
	let g:cmd="enter"
	pyfile git/Vim-ShareLaTex-Plugin/client.py
endfunction

function Sharelatex_update_pos()
	let g:cmd="updatePos"
	pyfile git/Vim-ShareLaTex-Plugin/client.py
endfunction

function Sharelatex_close()
	let g:cmd="close"
	pyfile git/Vim-ShareLaTex-Plugin/client.py
endfunction
