module TestKS

open FStar.HyperHeap
open FStar.HyperStack
open FStar.ST

open Platform.Bytes
open TLSConstants
open Parse

module CDH = CommonDH
module CC = CoreCrypto
module KS = KeySchedule

let p = IO.print_string
let pT = IO.debug_print_string

let main () : ML unit =
  p "Starting KeySchedule tests (based on draft-ietf-tls-tls13-vectors-00).\n";
  p " Replacing the keygen function in Curve25519... ";

  // Called by CommonDH.keygen. Replaced with the test vector ephemerals
  Curve25519.rand := (
    let ctr = ralloc root 0 in
    let gen (n:nat) : ST (lbytes n) (requires fun h -> True) (ensures fun h0 _ h1 -> modifies_none h0 h1) =
      let b = pT (" ...keygen call "^(string_of_int !ctr)^"... ") in
      let r =
       if !ctr = 0 then
        bytes_of_hex "00b4198a84ed6a7c218702891735239d40b7c665053303643d3c67f7458ecbc9"
       else
        bytes_of_hex "03d43f48ed52076f4ce9bab73d1f39ec689cf304075829f52b90f9f13bea6f34"
      in ctr := !ctr+1;
      fst (split r n)
    in gen);

  p "OK.\n Creating KS instances... ";
  let rc = new_region root in
  let rs = new_region root in
  let ksc, cr = KS.create #rc Client in
  let kss, sr = KS.create #rs Server in
  p "OK.\n Generating client shares... ";
  let ((CDH.Share g gx) :: _) = KS.ks_client_13_1rtt_init ksc [SEC (CC.ECC_X25519)] in
  p "OK.\n";
  let gx : Curve25519.point = gx in
  p ("\t -- gx = "^(hex_of_bytes gx)^"\n");
  (*
  p "OK.\n Rewriting the shares in the state with the test ephemerals:\n";
  p "\t Secret = 00b4198a84ed6a7c 218702891735239d 40b7c66505330364 3d3c67f7458ecbc9\n";
  p "\t Point  = 35e58b160db6124f 01a1d2475a22b72a bd6896701eed4c7e fd6124ee231ba458\n";
  let share:Curve25519.keyshare =
    (bytes_of_hex "35e58b160db6124f01a1d2475a22b72abd6896701eed4c7efd6124ee231ba458",
     bytes_of_hex "00b4198a84ed6a7c218702891735239d40b7c665053303643d3c67f7458ecbc9") in
  let gx = (| CDH.ECDH CC.ECC_X25519, share |) in
  ksc.KS.state := KS.C (KS.C_13_wait_SH cr None None [gx]);
  *)
  let cs = CipherSuite Kex_ECDHE (Some CC.RSASIG) (AEAD CC.AES_128_GCM Hashing.Spec.SHA256) in
  p " Generating server share... ";
  let (CDH.Share g gy) = KS.ks_server_13_1rtt_init kss cr cs g gx in
  p "OK.\n";
  let gy : Curve25519.point = gy in
  p ("\t gx = "^(hex_of_bytes gx)^"\n\t gy = "^(hex_of_bytes gy)^"\n");
  ()