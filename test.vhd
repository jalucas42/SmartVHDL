
entity test is 
  GENERIC (
    data_width                   : integer          := 3;
    addr_width                   : natural               
  );
  PORT (
    -- clocks and resets
    clk_g                        : IN STD_LOGIC                                      ;
    arstz_gq                     : IN STD_LOGIC                                      ;
    
    in_ivalid_gq                 : IN STD_LOGIC                                      ;
    in_data_gq                   : IN STD_LOGIC_VECTOR(data_width-1 DOWNTO 0)         
  );
end ENTITY test;


ARCHITECTURE bhv OF test is

  SUBTYPE test_data_t IS UNSIGNED(3 DOWNTO 0);
  TYPE test_data_array_t IS ARRAY(NATURAL RANGE <>) OF test_data_t;

  -- FIXME: Alignment behaves differently if the SIGNAL blocks below are separated by an empty line or a line with space.
  --        If a blank line, then each block is aligned separately.  If a line with spaces, then they are aligned as a 
  --        single block.  Not sure what the intended behavior is, but would prefer if each block is aligned separately always.
  
    -- abc comment
  SIGNAL test_signal1_gq              : STD_LOGIC                   ; -- fdsfsdf
  SIGNAL test_signal1_gq              : STD_LOGIC_VECTOR(3 DOWNTO 0); -- fdsfsdf

     SIGNAL test_signal2_gq              : STD_LOGIC_VECTOR(ADDR_WIDTH-1 DOWNTO 0)             ; -- 123
  SIGNAL test_signal3_gq              : STD_LOGIC_VECTOR(ADDR_WIDTH+DATA_WIDTH*2-1 DOWNTO 0); --    --def

      SIGNAL test_signal2_gq              : STD_LOGIC_VECTOR(ADDR_WIDTH-1 DOWNTO 0)             ; -- 123
  
BEGIN

  i_test : test
    GENERIC MAP (
      data_width                   => 3                           ,
      ADDR_WIDTH                   => ADDR_WIDTH*2                 
    )
    PORT MAP (
      -- Clocks and resets
      clk_g                        => clk_g                       ,
      arstz_gq                     => arstz_gq                    ,
      
      -- Input video
      in_ivalid_gq                 => in_ivalid_gq                ,
      in_data_gq                   => in_data_gq                   
    );



  
END bhv;
