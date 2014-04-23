
let g:nothing=""
function Sharelatex()
	let g:cmd="start"
	pyfile test.py
endfunction

function Sharelatex_project_up()
	let g:cmd="up"
	pyfile test.py
endfunction

function Sharelatex_project_down()
	let g:cmd="down"
	pyfile test.py
endfunction

function Sharelatex_project_enter()
	let g:cmd="enter"
	pyfile test.py
endfunction

function Sharelatex_update_pos()
	let g:cmd="updatePos"
	pyfile test.py
endfunction
