achilterm={};
achilterm.Terminal_ctor=function(id,width,height) {
	var ie=0;
	if(window.ActiveXObject)
		ie=1;
	var chrome = navigator.userAgent.match('Chrome');
	var webkit = navigator.userAgent.match('WebKit');
	var sid=""+Math.round(Math.random()*1000000000);
	var query0="s="+sid+"&w="+width+"&h="+height;
	var query1=query0+"&c=1&k=";
	var buf="";
	var timeout;
	var keybuf=[];
	var sending=0;
	var rmax=1;

	var div=document.getElementById(id);
	var dterm=document.createElement('div');

	function update() {
		if(sending==0) {
			sending=1;
			var r=new XMLHttpRequest();
			var send="";
			while(keybuf.length>0) {
				send+=keybuf.pop();
			}
			var query=query1+send;
			r.open("POST","u",true);
			r.setRequestHeader('Content-Type','application/x-www-form-urlencoded');
			r.onreadystatechange = function () {
				if (r.readyState==4) {
					if(r.status==200) {
						de=r.responseXML.documentElement;
						if(de.tagName=="pre") {
                    					dterm.innerHTML = r.responseText;
							rmax=100;
						} else {
							rmax*=2;
							if(rmax>2000)
								rmax=2000;
						}
						sending=0;
						timeout=window.setTimeout(update,rmax);
					}
				}
			}
			r.send(query);
		}
	}
	function queue(s) {
		keybuf.unshift(s);
		if(sending==0) {
			window.clearTimeout(timeout);
			timeout=window.setTimeout(update,1);
		}
	}
	function keypress(ev) {
		if (!ev) var ev=window.event;
		var kc;
		var k="";
		if (ev.keyCode)
			kc=ev.keyCode;
		if (ev.which)
			kc=ev.which;
		if (ev.altKey) {
			if (kc>=65 && kc<=90)
				kc+=32;
			if (kc>=97 && kc<=122) {
				k=String.fromCharCode(27)+String.fromCharCode(kc);
			}
		} else if (ev.ctrlKey) {
			if (kc>=65 && kc<=90) k=String.fromCharCode(kc-64); // Ctrl-A..Z
			else if (kc>=97 && kc<=122) k=String.fromCharCode(kc-96); // Ctrl-A..Z
			else if (kc==54)  k=String.fromCharCode(30); // Ctrl-^
			else if (kc==109) k=String.fromCharCode(31); // Ctrl-_
			else if (kc==219) k=String.fromCharCode(27); // Ctrl-[
			else if (kc==220) k=String.fromCharCode(28); // Ctrl-\
			else if (kc==221) k=String.fromCharCode(29); // Ctrl-]
			else if (kc==219) k=String.fromCharCode(29); // Ctrl-]
			else if (kc==219) k=String.fromCharCode(0);  // Ctrl-@
		} else if (ev.which==0) {
			if (kc==9) k=String.fromCharCode(9);  // Tab
			else if (kc==8) k=String.fromCharCode(127);  // Backspace
			else if (kc==27) k=String.fromCharCode(27); // Escape
			else {
				if (kc==33) k="[5~";        // PgUp
				else if (kc==34) k="[6~";   // PgDn
				else if (kc==35) k="[4~";   // End
				else if (kc==36) k="[1~";   // Home
				else if (kc==37) k="[D";    // Left
				else if (kc==38) k="[A";    // Up
				else if (kc==39) k="[C";    // Right
				else if (kc==40) k="[B";    // Down
				else if (kc==45) k="[2~";   // Ins
				else if (kc==46) k="[3~";   // Del
				else if (kc==112) k="[[A";  // F1
				else if (kc==113) k="[[B";  // F2
				else if (kc==114) k="[[C";  // F3
				else if (kc==115) k="[[D";  // F4
				else if (kc==116) k="[[E";  // F5
				else if (kc==117) k="[17~"; // F6
				else if (kc==118) k="[18~"; // F7
				else if (kc==119) k="[19~"; // F8
				else if (kc==120) k="[20~"; // F9
				else if (kc==121) k="[21~"; // F10
				else if (kc==122) k="[23~"; // F11
				else if (kc==123) k="[24~"; // F12
				if (k.length) {
					k=String.fromCharCode(27)+k;
				}
			}
		} else {
			if (kc==8)
				k=String.fromCharCode(127);  // Backspace
			else
				k=String.fromCharCode(kc);
		}
		if(k.length) {
			if(k=="+") {
				queue("%2B");
			} else {
				queue(encodeURIComponent(k));
			}
		}
		ev.cancelBubble=true;
		if (ev.stopPropagation) ev.stopPropagation();
		if (ev.preventDefault)  ev.preventDefault();
		return false;
	}
	function keydown(ev) {
		if (!ev) var ev=window.event;
		if (ie || chrome || webkit) {
			o={9:1,8:1,27:1,33:1,34:1,35:1,36:1,37:1,38:1,39:1,40:1,45:1,46:1,112:1,
			113:1,114:1,115:1,116:1,117:1,118:1,119:1,120:1,121:1,122:1,123:1};
			if (o[ev.keyCode] || ev.ctrlKey || ev.altKey) {
				ev.which=0;
				return keypress(ev);
			}
		}
	}
	function init() {
		div.appendChild(dterm);
		document.onkeypress=keypress;
		document.onkeydown=keydown;
		timeout=window.setTimeout(update,100);
	}
	init();
}
achilterm.Terminal=function(id,width,height) {
	return new this.Terminal_ctor(id,width,height);
}
