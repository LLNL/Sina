program example
  use sina_functions
  implicit none

  ! data types
  integer (KIND=4) :: int_val
  integer (KIND=8) :: long_val
  real :: real_val
  double precision :: double_val
  character :: char_val
  logical :: is_val
  integer :: i
  logical :: independent
  
  ! 1D real Array
  real, dimension(20) :: real_arr
  double precision, dimension(20) :: double_arr
  
  
  ! Strings
  character(:), allocatable :: fle_nme
  character(:), allocatable :: ofle_nme
  character(17) :: wrk_dir
  character(29) :: full_path
  character(36) :: ofull_path
  character(:), allocatable  :: rec_id
  character(:), allocatable :: mime_type
  character(:), allocatable :: tag
  character(:), allocatable :: units 
  character(20) :: json_fn
  character(15) :: name
  character(25) :: curve
  
  ! 1D integer Array
  integer, dimension(20) :: int_arr
  integer (kind=8), dimension(20) :: long_arr
  
  int_val = 10
  long_val = 1000000000
  real_val = 1.234567
  double_val = 1./1.2345678901234567890123456789
  char_val = 'A'
  is_val = .false.
  
  do i = 1, 20
    real_arr(i) = i
    double_arr(i) = i*2.
    int_arr(i) = i*3
    long_arr(i) = i*4
  end do
  
  rec_id = 'my_rec_id'
  fle_nme = 'my_file.txt'
  ofle_nme = 'my_other_file.txt'
  wrk_dir = '/path/to/my/file/'
  full_path = wrk_dir//''//fle_nme
  ofull_path = wrk_dir//''//ofle_nme
  json_fn = 'sina_dump.json'
  
  
  mime_type = ''
  units = ''
  tag = ''
  
  print *,rec_id

  ! ========== USAGE ==========
  
  ! create sina record and document
  print *,'Creating the document'
  call create_document_and_record(trim(rec_id)//char(0))
  
  ! add file to sina record
  print *,'Adding a file to the Sina record'
  call sina_add_file(trim(full_path)//char(0), mime_type)
  mime_type = 'png'
  print *,'Adding another file (PNG) to the Sina record'
  call sina_add_file(trim(ofull_path)//char(0), mime_type)
  print *, "Adding int", int_val
  name = 'int'
  call sina_add(trim(name)//char(0), int_val, units, tag)
  print *, "Adding logical"
  name = 'logical'
  call sina_add(trim(name)//char(0), is_val, units, tag)
  print *, "Adding long"
  name = 'long'
  call sina_add(trim(name)//char(0), long_val, units, tag)
  print *, "Adding real"
  name = 'real'
  call sina_add(trim(name)//char(0), real_val, units, tag)
  print *, "Adding double"
  name = 'double'
  call sina_add(trim(name)//char(0), double_val, units, tag)
  print *, "Adding char"
  name = 'char'
  call sina_add(trim(name)//char(0), trim(char_val)//char(0), units, tag)
  units = "kg"
  print *, "Adding int", int_val
  name = 'u_int'
  call sina_add(trim(name)//char(0), int_val, trim(units)//char(0), tag)
  print *, "Adding logical"
  name = 'u_logical'
  is_val = .true.
  call sina_add(trim(name)//char(0), is_val, trim(units)//char(0), tag)
  print *, "Adding long"
  name = 'u_long'
  call sina_add(trim(name)//char(0), long_val, trim(units)//char(0), tag)
  print *, "Adding real"
  name = 'u_real'
  call sina_add(trim(name)//char(0), real_val, trim(units)//char(0), tag)
  print *, "Adding double"
  name = 'u_double'
  call sina_add(trim(name)//char(0), double_val, trim(units)//char(0), tag)
  
  print *, "Adding double with tag"
  name = 'u_double_w_tag'
  tag = 'new_fancy_tag'
  call sina_add(trim(name)//char(0), double_val, trim(units)//char(0), tag)
  
  deallocate(tag)
  print *, "Adding char"
  name = 'u_char'
  call sina_add(trim(name)//char(0), trim(char_val)//char(0), trim(units)//char(0), tag)
 
  name = "my_curveset"
  name = trim(name)//char(0)
  call sina_add_curveset(name)

  curve = "my_indep_curve_double"
  curve = trim(curve)//char(0)
  independent = .TRUE.
  call sina_add_curve(name, curve, double_arr, size(double_arr), independent)
  curve = "my_indep_curve_real"
  curve = trim(curve)//char(0)
  call sina_add_curve(name, curve, real_arr, size(real_arr), independent)
  curve = "my_indep_curve_int"
  curve = trim(curve)//char(0)
  call sina_add_curve(name, curve, int_arr, size(int_arr), independent)
  curve = "my_indep_curve_long"
  curve = trim(curve)//char(0)
  call sina_add_curve(name, curve, long_arr, size(long_arr), independent)
  curve = "my_dep_curve_double"
  curve = trim(curve)//char(0)
  independent = .false.
  call sina_add_curve(name, curve, double_arr, size(double_arr), independent)
  curve = "my_dep_curve_double_2"
  curve = trim(curve)//char(0)
  call sina_add_curve(name, curve, double_arr, size(double_arr), independent)
  curve = "my_dep_curve_real"
  curve = trim(curve)//char(0)
  call sina_add_curve(name, curve, real_arr, size(real_arr), independent)
  curve = "my_dep_curve_int"
  curve = trim(curve)//char(0)
  call sina_add_curve(name, curve, int_arr, size(int_arr), independent)
  curve = "my_dep_curve_long"
  curve = trim(curve)//char(0)
  call sina_add_curve(name, curve, long_arr, size(long_arr), independent)
  ! write out the Sina Document
  print *,'Writing out the Sina Document'
  call write_sina_document(trim(json_fn)//char(0))

  
  
  

end program example
